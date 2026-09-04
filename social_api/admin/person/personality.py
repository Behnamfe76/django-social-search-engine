from django.contrib import admin

from social_api.admin.attribute.inlines import (
    PersonalityCertificationInline,
    PersonalityInterestInline,
    PersonalityLanguageInline,
    PersonalitySkillInline,
)
from social_api.models import Personality


@admin.register(Personality)
class PersonalityAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "gender", "industry", "created_at")
    list_select_related = ("industry",)
    exclude = ("deleted_at",)
    list_filter = ("gender",)
    search_fields = ("full_name", "first_name", "last_name")
    autocomplete_fields = ("industry",)
    inlines = (
        PersonalitySkillInline,
        PersonalityInterestInline,
        PersonalityLanguageInline,
        PersonalityCertificationInline,
    )
    ordering = ("full_name",)
    readonly_fields = ("id", "full_name", "created_at", "updated_at", "deleted_at")
