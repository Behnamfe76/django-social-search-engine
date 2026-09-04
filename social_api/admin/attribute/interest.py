from django.contrib import admin

from social_api.models import Interest


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
