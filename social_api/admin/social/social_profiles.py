from django.contrib import admin

from social_api.models import SocialProfiles


@admin.register(SocialProfiles)
class SocialProfilesAdmin(admin.ModelAdmin):
    list_display = ("id", "personality", "social_platform", "user_name", "url", "connection_count")
    list_filter = ("social_platform",)
    search_fields = ("user_name", "platform_user_id", "url", "personality__full_name")
    autocomplete_fields = ("personality", "social_platform")
    ordering = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
