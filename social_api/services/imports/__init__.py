"""Chunked, out-of-request ingestion of uploaded profile datasets."""

from social_api.services.imports.chunking import ChunkSpan, iter_record_spans, plan_chunks
from social_api.services.imports.reader import SourceRow, iter_rows, read_range
from social_api.services.imports.references import References
from social_api.services.imports.row_importer import ChunkImporter, ChunkResult

__all__ = [
    "ChunkImporter",
    "ChunkResult",
    "ChunkSpan",
    "References",
    "SourceRow",
    "iter_record_spans",
    "iter_rows",
    "plan_chunks",
    "read_range",
]
