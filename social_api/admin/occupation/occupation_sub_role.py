from django.contrib import admin

from social_api.models import OccupationSubRole


@admin.register(OccupationSubRole)
class OccupationSubRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "slug", "occupation_role")
    list_select_related = ("occupation_role",)
    list_filter = ("occupation_role",)
    search_fields = ("title", "slug", "occupation_role__title")
    autocomplete_fields = ("occupation_role",)
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("occupation_role__title", "title")
    readonly_fields = ("id", "created_at", "updated_at")
