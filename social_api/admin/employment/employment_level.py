from django.contrib import admin

from social_api.models import EmploymentLevel


class EmploymentLevelInline(admin.TabularInline):
    """EmploymentLevel has a composite primary key, which the admin cannot register
    as a standalone ModelAdmin, so it is edited inline on Employment instead."""

    model = EmploymentLevel
    autocomplete_fields = ("occupation_level",)
    extra = 0
