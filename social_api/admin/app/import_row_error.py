from django.contrib import admin

from social_api.models import ImportRowError


@admin.register(ImportRowError)
class ImportRowErrorAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "row_number", "message", "created_at")
    list_select_related = ("batch",)
    search_fields = ("message", "batch__filename")
    ordering = ("batch", "row_number")
    readonly_fields = ("id", "batch", "chunk", "row_number", "message", "excerpt", "created_at")

    def has_add_permission(self, request):
        return False
