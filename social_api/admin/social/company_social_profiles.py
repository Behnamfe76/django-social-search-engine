from django.contrib import admin

from social_api.models import CompanySocialProfiles


@admin.register(CompanySocialProfiles)
class CompanySocialProfilesAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "social_platform", "user_name", "url")
    list_filter = ("social_platform",)
    search_fields = ("user_name", "platform_user_id", "url", "company__name")
    autocomplete_fields = ("company", "social_platform")
    ordering = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
