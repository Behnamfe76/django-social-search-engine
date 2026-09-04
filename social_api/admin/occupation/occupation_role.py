from django.contrib import admin

from social_api.models import OccupationRole


@admin.register(OccupationRole)
class OccupationRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "slug")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")
