import csv
import io

from django.test import SimpleTestCase

from social_api.services.imports.chunking import iter_record_spans, plan_chunks
from social_api.services.imports.reader import iter_rows

# A quoted field is allowed to contain a literal newline, and the real export
# uses that: 357 physical lines carrying 337 records.
EMBEDDED_NEWLINE = 'a,b\n1,"line one\nline two"\n2,"plain"\n'


def spans_of(document, **kwargs):
    return list(iter_record_spans(io.BytesIO(document.encode()), **kwargs))


class RecordScannerTests(SimpleTestCase):
    def test_plain_records_split_on_newlines(self):
        self.assertEqual(len(spans_of("a,b\n1,x\n2,y\n")), 3)

    def test_newline_inside_a_quoted_field_is_not_a_boundary(self):
        self.assertEqual(len(spans_of(EMBEDDED_NEWLINE)), 3)

    def test_doubled_quotes_do_not_flip_the_quote_state(self):
        document = 'a,b\n1,"say ""hi"", then\nnewline"\n2,y\n'

        self.assertEqual(len(spans_of(document)), 3)

    def test_final_record_without_a_trailing_newline_is_kept(self):
        document = "a,b\n1,x"
        spans = spans_of(document)

        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[-1][1], len(document))

    def test_spans_tile_the_document_exactly(self):
        raw = EMBEDDED_NEWLINE.encode()
        spans = spans_of(EMBEDDED_NEWLINE)

        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[-1][1], len(raw))
        for (_, end), (next_start, _) in zip(spans, spans[1:]):
            self.assertEqual(end, next_start)

    def test_a_block_smaller_than_a_record_gives_the_same_answer(self):
        """The scanner must survive refills landing mid-field, mid-quote, anywhere."""
        expected = spans_of(EMBEDDED_NEWLINE)

        for block_size in (1, 2, 3, 5, 7, 13):
            with self.subTest(block_size=block_size):
                self.assertEqual(spans_of(EMBEDDED_NEWLINE, block_size=block_size), expected)

    def test_empty_document_yields_nothing(self):
        self.assertEqual(spans_of(""), [])


class ChunkPlannerTests(SimpleTestCase):
    def plan(self, document, **kwargs):
        header_end, chunks = plan_chunks(io.BytesIO(document.encode()), **kwargs)
        return header_end, list(chunks)

    def test_header_is_reported_separately_from_the_chunks(self):
        document = "a,b\n1,x\n2,y\n"
        header_end, chunks = self.plan(document, max_rows=10)

        self.assertEqual(header_end, len("a,b\n"))
        self.assertEqual(chunks[0].start, header_end)
        self.assertEqual(sum(chunk.row_count for chunk in chunks), 2)

    def test_row_ceiling_closes_a_chunk(self):
        document = "a\n" + "".join(f"{index}\n" for index in range(10))
        _, chunks = self.plan(document, max_rows=3, target_bytes=10**6)

        self.assertEqual([chunk.row_count for chunk in chunks], [3, 3, 3, 1])

    def test_byte_ceiling_closes_a_chunk(self):
        document = "a\n" + "".join(f"{'x' * 20}\n" for _ in range(6))
        _, chunks = self.plan(document, max_rows=10**6, target_bytes=40)

        self.assertTrue(len(chunks) > 1)
        self.assertTrue(all(chunk.length >= 40 for chunk in chunks[:-1]))

    def test_first_row_accumulates_across_chunks(self):
        document = "a\n" + "".join(f"{index}\n" for index in range(10))
        _, chunks = self.plan(document, max_rows=4, target_bytes=10**6)

        self.assertEqual([chunk.first_row for chunk in chunks], [1, 5, 9])

    def test_blank_lines_are_not_rows(self):
        document = "a,b\n1,x\n\n2,y\n\n"
        _, chunks = self.plan(document, max_rows=10)

        self.assertEqual(sum(chunk.row_count for chunk in chunks), 2)

    def test_chunks_are_contiguous_and_indexed(self):
        document = "a\n" + "".join(f"{index}\n" for index in range(10))
        header_end, chunks = self.plan(document, max_rows=3, target_bytes=10**6)

        self.assertEqual([chunk.index for chunk in chunks], [0, 1, 2, 3])
        self.assertEqual(chunks[0].start, header_end)
        for chunk, following in zip(chunks, chunks[1:]):
            self.assertEqual(chunk.end, following.start)


class ChunkReaderTests(SimpleTestCase):
    def test_header_is_prepended_so_a_chunk_parses_alone(self):
        rows = list(iter_rows(b"a,b\n", b"1,x\n2,y\n"))

        self.assertEqual([row.values for row in rows], [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}])

    def test_rows_are_numbered_from_the_chunk_offset(self):
        rows = list(iter_rows(b"a,b\n", b"1,x\n2,y\n", first_row=51))

        self.assertEqual([row.number for row in rows], [51, 52])

    def test_a_ragged_row_is_reported_not_raised(self):
        rows = list(iter_rows(b"a,b\n", b"1,x\n2,y,z\n"))

        self.assertTrue(rows[0].ok)
        self.assertFalse(rows[1].ok)
        self.assertIn("expected 2 columns, got 3", rows[1].error)
        self.assertEqual(rows[1].excerpt, "2,y,z")

    def test_a_quoted_newline_survives_the_round_trip(self):
        _, body = EMBEDDED_NEWLINE.split("\n", 1)
        rows = list(iter_rows(b"a,b\n", body.encode()))

        self.assertEqual(rows[0].values["b"], "line one\nline two")


class ScannerAgreesWithCsvReaderTests(SimpleTestCase):
    """The planned row count is only honest if the planner splits where the reader does.

    A quote opens a quoted field only at the start of a field. Treating every
    quote as significant merges records the reader later splits, and the batch
    then advertises fewer rows than the workers import.
    """

    DOCUMENTS = [
        "a,b\n1,x\n",
        'a,b\n1,"line one\nline two"\n2,y\n',
        'a,b\n1,"say ""hi"", ok"\n2,y\n',
        # Stray quotes in the middle of an unquoted field: literal data.
        'a,b\n1,5" nails\n2,y\n',
        'a,b\n1,he said "no" loudly\n2,y\n',
        # Text trailing a closing quote, which non-strict readers keep.
        'a,b\n1,"quoted"tail\n2,y\n',
        "a,b\n1,x\n\n2,y\n",
        "a,b\n,,\n2,y\n",
        "a,b\n1,x",
        'a,b\n1,"unterminated\n',
    ]

    def test_record_counts_agree(self):
        for document in self.DOCUMENTS:
            with self.subTest(document=document):
                expected = [row for row in csv.reader(io.StringIO(document)) if row]

                self.assertEqual(len(spans_of(document)), len(expected))

    def test_every_span_reparses_to_exactly_one_record(self):
        """What each worker relies on: its slice is a whole number of records."""
        for document in self.DOCUMENTS:
            raw = document.encode()
            for start, end in spans_of(document):
                with self.subTest(document=document, span=(start, end)):
                    piece = raw[start:end].decode()
                    records = [row for row in csv.reader(io.StringIO(piece)) if row]

                    self.assertEqual(len(records), 1)
