from django.contrib import admin

from social_api.models import (
    PersonalityCertification,
    PersonalityInterest,
    PersonalityLanguage,
    PersonalitySkill,
)


class PersonalitySkillInline(admin.TabularInline):
    """Composite primary key, so it is edited inline on Personality."""

    model = PersonalitySkill
    autocomplete_fields = ("skill",)
    extra = 0


class PersonalityInterestInline(admin.TabularInline):
    """Composite primary key, so it is edited inline on Personality."""

    model = PersonalityInterest
    autocomplete_fields = ("interest",)
    extra = 0


class PersonalityLanguageInline(admin.TabularInline):
    """Composite primary key, so it is edited inline on Personality."""

    model = PersonalityLanguage
    autocomplete_fields = ("language",)
    extra = 0


class PersonalityCertificationInline(admin.TabularInline):
    model = PersonalityCertification
    autocomplete_fields = ("certification",)
    extra = 0
