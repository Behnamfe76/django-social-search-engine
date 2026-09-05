"""Reading a planned chunk back out of storage and into parsed rows."""

import csv
import io
from dataclasses import dataclass

# Some cells in this export (the nested ``experience`` blob) run to tens of
# kilobytes, well past the 128 KB default once a row is unusually large.
MAX_FIELD_BYTES = 10 * 1024 * 1024
csv.field_size_limit(MAX_FIELD_BYTES)

EXCERPT_LIMIT = 500


@dataclass(frozen=True)
class SourceRow:
    """One record from the file, aligned to the header or rejected."""

    number: int  # 1-based position within the whole source file
    values: dict | None  # None when the record could not be aligned
    excerpt: str
    error: str | None

    @property
    def ok(self) -> bool:
        return self.values is not None


def read_range(storage, name: str, start: int, end: int) -> bytes:
    """Return the bytes of ``[start, end)``.

    Local storage seeks; S3 would answer the identical call with a ranged GET.
    Addressing chunks by offset is what keeps those two interchangeable.
    """
    with storage.open(name, "rb") as handle:
        handle.seek(start)
        return handle.read(end - start)


def iter_rows(header_bytes: bytes, body_bytes: bytes, *, first_row: int = 1):
    """Yield ``SourceRow``s for one chunk, header prepended.

    Rows whose column count does not match the header are yielded as errors
    rather than raised: the sample export alone carries 53 of them, and dropping
    283 good profiles to fix 53 bad ones is the wrong trade.
    """
    header = next(csv.reader(io.StringIO(_decode(header_bytes))), [])
    width = len(header)
    number = first_row

    for fields in csv.reader(io.StringIO(_decode(body_bytes))):
        if not fields or (len(fields) == 1 and not fields[0].strip()):
            continue

        excerpt = ",".join(fields)[:EXCERPT_LIMIT]
        if len(fields) != width:
            yield SourceRow(
                number,
                None,
                excerpt,
                f"expected {width} columns, got {len(fields)}",
            )
        else:
            yield SourceRow(number, dict(zip(header, fields)), excerpt, None)
        number += 1


def _decode(raw: bytes) -> str:
    # utf-8-sig so a byte-order mark on the header does not become part of the
    # first column name; replace so one bad byte cannot fail a whole chunk.
    return raw.decode("utf-8-sig", errors="replace")
