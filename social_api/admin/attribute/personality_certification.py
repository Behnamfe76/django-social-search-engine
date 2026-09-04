from django.contrib import admin

from social_api.models import PersonalityCertification


@admin.register(PersonalityCertification)
class PersonalityCertificationAdmin(admin.ModelAdmin):
    list_display = ("id", "personality", "certification", "start_date", "end_date")
    list_select_related = ("personality", "certification")
    search_fields = ("personality__full_name", "certification__name")
    autocomplete_fields = ("personality", "certification")
    ordering = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
