from django.contrib import admin

from social_api.admin.app.import_chunk import ImportChunkInline
from social_api.models import ImportBatch


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source",
        "filename",
        "status",
        "progress",
        "row_count",
        "failed_rows",
        "user",
        "created_at",
    )
    list_select_related = ("user",)
    list_filter = ("status", "source")
    search_fields = ("source", "filename", "user__email")
    autocomplete_fields = ("user",)
    inlines = (ImportChunkInline,)
    ordering = ("-created_at",)
    # Everything here is written by the workers; the admin is a read-only window.
    readonly_fields = (
        "id",
        "status",
        "file",
        "file_size",
        "header_end",
        "row_count",
        "total_chunks",
        "pending_chunks",
        "processed_rows",
        "created_rows",
        "updated_rows",
        "failed_rows",
        "progress",
        "duration_seconds",
        "error",
        "started_at",
        "finished_at",
        "created_at",
    )

    @admin.display(description="progress")
    def progress(self, obj):
        return f"{obj.progress}%"
