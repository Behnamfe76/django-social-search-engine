from django.contrib import admin

from social_api.models import Personality


@admin.register(Personality)
class PersonalityAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "gender", "industry_id", "created_at")
    list_filter = ("gender",)
    search_fields = ("full_name", "first_name", "last_name")
