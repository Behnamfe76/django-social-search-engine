from django.contrib import admin

from social_api.admin.employment.employment_level import EmploymentLevelInline
from social_api.models import Employment


@admin.register(Employment)
class EmploymentAdmin(admin.ModelAdmin):
    list_display = ("id", "personality", "company", "title", "occupation", "is_current", "start_date")
    list_select_related = ("personality", "company", "occupation")
    list_filter = ("is_current",)
    search_fields = ("title", "personality__full_name", "company__name")
    autocomplete_fields = (
        "personality",
        "company",
        "location",
        "occupation",
        "occupation_role",
        "occupation_sub_role",
    )
    inlines = (EmploymentLevelInline,)
    ordering = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
