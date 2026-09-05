from rest_framework.pagination import CursorPagination, PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Project-wide default; wired in via REST_FRAMEWORK.DEFAULT_PAGINATION_CLASS."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LookupCursorPagination(CursorPagination):
    """Cursor paging for the reference lists the filter widgets read.

    Cursor rather than page-number because these lists are picked through while
    the importer is still writing to them: an offset page 3 would skip or repeat
    rows as names are inserted above the window, and a keyset cursor cannot.

    ``ordering`` must stay a total order. DRF seeks with a strict ``name__gt``
    and walks equal names with an offset, so ties need a deterministic
    tie-break or a cursor can land mid-run and drop rows.
    """

    page_size = 25
    ordering = ("pk")
