from django.db.models import QuerySet

from social_api.models import ImportBatch, ImportRowError


def import_batch_queryset() -> QuerySet[ImportBatch]:
    return ImportBatch.objects.select_related("user").order_by("-created_at")


def import_row_error_queryset(batch) -> QuerySet[ImportRowError]:
    return ImportRowError.objects.filter(batch=batch).order_by("row_number")
