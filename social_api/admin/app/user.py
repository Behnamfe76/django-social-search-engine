from django.contrib import admin

from social_api.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin for the application ``users`` table.

    Distinct from ``django.contrib.auth`` users, which still back admin login.
    """

    list_display = ("id", "email", "name", "personality", "created_at")
    list_select_related = ("personality",)
    search_fields = ("email", "name", "personality__full_name")
    autocomplete_fields = ("personality",)
    exclude = ("password_hash", "deleted_at")
    ordering = ("email",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
