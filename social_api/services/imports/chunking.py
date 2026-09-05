"""Record-aligned chunk planning for uploaded CSV files.

The planner walks the file once in fixed-size blocks and never holds more than one
block plus its scan cursor, so planning a 100 GB export costs the same memory as
planning a 5 MB one. Record *contents* are never buffered: a chunk is described by
a pair of byte offsets, and the bytes themselves are read later by whichever worker
picks the chunk up.

Splitting on newlines would not work. RFC 4180 lets a quoted field contain a
literal newline, and this dataset uses that freedom -- the sample export is 357
physical lines but only 337 records. The scanner therefore tracks whether it sits
inside a quoted field, which is cheap to do because it reads sequentially from
byte zero.

Its state machine mirrors CPython's ``csv`` reader byte for byte, which matters
more than it sounds: a quote only opens a quoted field at the *start* of a field,
and elsewhere it is ordinary data. Treating every quote as a delimiter makes the
planner merge records that the reader later splits, and the row count it
advertises stops matching the rows the workers actually import.
"""

from dataclasses import dataclass
from typing import BinaryIO, Iterable, Iterator

QUOTE = ord('"')
NEWLINE = ord("\n")
CARRIAGE_RETURN = ord("\r")
DELIMITER = ord(",")
TERMINATORS = frozenset({NEWLINE, CARRIAGE_RETURN})

# Scanner states, named after the ones in CPython's _csv module.
_FIELD_START = 0
_IN_FIELD = 1
_IN_QUOTED = 2
_QUOTE_IN_QUOTED = 3

DEFAULT_BLOCK_BYTES = 1024 * 1024
DEFAULT_TARGET_BYTES = 1024 * 1024
DEFAULT_MAX_ROWS = 500

# Bytes of already-scanned buffer kept behind the cursor. Two is enough to look
# back at a record that turned out to be nothing but a line terminator.
_HISTORY_BYTES = 2


@dataclass(frozen=True)
class ChunkSpan:
    """One unit of work: a half-open byte range covering whole records."""

    index: int
    start: int
    end: int
    first_row: int
    row_count: int

    @property
    def length(self) -> int:
        return self.end - self.start


def iter_record_spans(
    stream: BinaryIO, *, block_size: int = DEFAULT_BLOCK_BYTES
) -> Iterator[tuple[int, int]]:
    """Yield ``(start, end)`` byte offsets, one per CSV record in ``stream``.

    Blank lines are skipped rather than reported as empty records, so the row
    count the planner arrives at is the row count the workers will import.
    """
    buf = bytearray()
    base = 0  # file offset of buf[0]
    cursor = 0  # scan position within buf
    start = 0  # file offset where the current record begins
    state = _FIELD_START
    exhausted = False

    while True:
        # Refill, discarding what has been scanned but keeping a couple of bytes
        # of history. The buffer therefore stays flat even when a single record is
        # larger than one block: record *contents* are never accumulated.
        if not exhausted and cursor >= len(buf):
            retained = min(cursor, _HISTORY_BYTES)
            del buf[: cursor - retained]
            base += cursor - retained
            cursor = retained
            block = stream.read(block_size)
            if block:
                buf += block
            else:
                exhausted = True

        if cursor >= len(buf):
            break

        byte = buf[cursor]

        if state == _IN_QUOTED:
            if byte == QUOTE:
                state = _QUOTE_IN_QUOTED
                cursor += 1
            else:
                # Inside quotes everything is data, newlines included.
                cursor = _seek(buf, cursor + 1, QUOTE)
            continue

        if state == _QUOTE_IN_QUOTED:
            if byte == QUOTE:  # "" is an escaped quote, the field continues
                state = _IN_QUOTED
            elif byte == DELIMITER:
                state = _FIELD_START
            elif byte == NEWLINE:
                cursor += 1
                end = base + cursor
                if not _is_blank(buf, cursor, end - start):
                    yield start, end
                start = end
                state = _FIELD_START
                continue
            else:
                # Text after a closing quote. Non-strict readers keep it, so so do we.
                state = _IN_FIELD
            cursor += 1
            continue

        if state == _FIELD_START:
            if byte == QUOTE:  # only here does a quote open a quoted field
                state = _IN_QUOTED
                cursor += 1
                continue
            if byte == DELIMITER:  # an empty field
                cursor += 1
                continue
            if byte == NEWLINE:
                cursor += 1
                end = base + cursor
                if not _is_blank(buf, cursor, end - start):
                    yield start, end
                start = end
                continue
            state = _IN_FIELD
            cursor += 1
            continue

        # _IN_FIELD: a quote here is ordinary data, not a delimiter.
        if byte == DELIMITER:
            state = _FIELD_START
            cursor += 1
            continue
        if byte == NEWLINE:
            cursor += 1
            end = base + cursor
            if not _is_blank(buf, cursor, end - start):
                yield start, end
            start = end
            state = _FIELD_START
            continue
        cursor = _seek2(buf, cursor + 1, DELIMITER, NEWLINE)

    tail = base + cursor
    if tail > start and not _is_blank(buf, cursor, tail - start):
        yield start, tail  # final record, unterminated


def _is_blank(buf: bytearray, cursor: int, length: int) -> bool:
    """True when the record that just closed held nothing but line terminators."""
    if length > _HISTORY_BYTES:
        return False
    return all(byte in TERMINATORS for byte in buf[max(cursor - length, 0) : cursor])


def _seek(buf: bytearray, offset: int, wanted: int) -> int:
    """Jump to the next ``wanted`` byte, or past the end of the buffer."""
    found = buf.find(wanted, offset)
    return len(buf) if found == -1 else found


def _seek2(buf: bytearray, offset: int, first: int, second: int) -> int:
    """Jump to whichever of two bytes comes first."""
    left = buf.find(first, offset)
    right = buf.find(second, offset)
    if left == -1:
        return len(buf) if right == -1 else right
    if right == -1:
        return left
    return min(left, right)


def plan_chunks(
    stream: BinaryIO,
    *,
    target_bytes: int = DEFAULT_TARGET_BYTES,
    max_rows: int = DEFAULT_MAX_ROWS,
    block_size: int = DEFAULT_BLOCK_BYTES,
) -> tuple[int, Iterator[ChunkSpan]]:
    """Return ``(header_end, chunks)`` for ``stream``.

    The header record is consumed eagerly so the caller can record where it ends;
    workers prepend those bytes to their own slice so every chunk parses as a
    standalone CSV document. The remaining records are streamed, never listed.
    """
    spans = iter_record_spans(stream, block_size=block_size)
    header = next(spans, None)
    if header is None:
        return 0, iter(())

    _, header_end = header
    return header_end, _group(spans, target_bytes=target_bytes, max_rows=max_rows)


def _group(
    spans: Iterable[tuple[int, int]], *, target_bytes: int, max_rows: int
) -> Iterator[ChunkSpan]:
    """Accumulate records into chunks bounded by both size and row count."""
    index = 0
    first_row = 1
    start = None
    end = 0
    rows = 0

    for span_start, span_end in spans:
        if start is None:
            start = span_start
        end = span_end
        rows += 1

        if end - start >= target_bytes or rows >= max_rows:
            yield ChunkSpan(index, start, end, first_row, rows)
            index += 1
            first_row += rows
            start = None
            rows = 0

    if start is not None:
        yield ChunkSpan(index, start, end, first_row, rows)
