from django.contrib import admin

from social_api.models import ImportChunk


class ImportChunkInline(admin.TabularInline):
    """Read-only view of how a batch was split and how each slice fared."""

    model = ImportChunk
    extra = 0
    can_delete = False
    fields = (
        "index",
        "status",
        "start_offset",
        "end_offset",
        "row_count",
        "created_rows",
        "updated_rows",
        "failed_rows",
        "error",
    )
    readonly_fields = fields
    ordering = ("index",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ImportChunk)
class ImportChunkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "batch",
        "index",
        "status",
        "row_count",
        "created_rows",
        "updated_rows",
        "failed_rows",
    )
    list_select_related = ("batch",)
    list_filter = ("status",)
    search_fields = ("batch__filename",)
    ordering = ("-batch", "index")
