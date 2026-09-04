from django.contrib import admin

from social_api.models import ImportBatch


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "filename", "row_count", "user", "created_at")
    list_select_related = ("user",)
    list_filter = ("source",)
    search_fields = ("source", "filename", "user__email")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at")
