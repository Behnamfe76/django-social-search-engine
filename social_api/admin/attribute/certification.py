from django.contrib import admin

from social_api.models import Certification


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "organization")
    list_filter = ("organization",)
    search_fields = ("name", "slug", "organization")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
