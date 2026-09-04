from django.contrib import admin

from social_api.models import PersonalityLocation


@admin.register(PersonalityLocation)
class PersonalityLocationAdmin(admin.ModelAdmin):
    list_display = ("id", "personality", "location", "street_address", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("personality__full_name", "street_address", "postal_code")
    autocomplete_fields = ("personality", "location")
    ordering = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
