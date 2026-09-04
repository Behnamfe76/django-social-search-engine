from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Project-wide default; wired in via REST_FRAMEWORK.DEFAULT_PAGINATION_CLASS."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
