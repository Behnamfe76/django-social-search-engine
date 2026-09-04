from django.contrib import admin

from social_api.models import OccupationLevel


@admin.register(OccupationLevel)
class OccupationLevelAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "slug")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")
