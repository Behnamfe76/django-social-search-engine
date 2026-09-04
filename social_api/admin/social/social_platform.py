from django.contrib import admin

from social_api.models import SocialPlatform


@admin.register(SocialPlatform)
class SocialPlatformAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "domain")
    search_fields = ("name", "slug", "domain")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
