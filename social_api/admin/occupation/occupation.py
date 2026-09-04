from django.contrib import admin

from social_api.models import Occupation


@admin.register(Occupation)
class OccupationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "slug", "industry")
    list_select_related = ("industry",)
    search_fields = ("title", "slug", "industry__name")
    autocomplete_fields = ("industry",)
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")
