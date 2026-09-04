from django.contrib import admin

from social_api.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "industry", "website", "size", "founded_year")
    list_select_related = ("industry",)
    list_filter = ("size",)
    search_fields = ("name", "slug", "website", "external_id")
    autocomplete_fields = ("industry", "location")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
