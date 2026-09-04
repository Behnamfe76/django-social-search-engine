from django.contrib import admin

from social_api.models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "locality", "region", "country", "continent")
    list_filter = ("name", "continent", "country")
    search_fields = ("locality", "metro", "region", "country", "continent")
    ordering = ("country", "region", "locality")
    readonly_fields = ("id", "created_at", "updated_at")
