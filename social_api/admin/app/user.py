from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm as BaseUserChangeForm

from social_api.models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "name")


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Uses the auth admin so the password is hashed, never edited as raw text."""

    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    list_display = ("id", "email", "name", "personality", "is_staff", "is_active", "created_at")
    list_select_related = ("personality",)
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "name", "personality__full_name")
    autocomplete_fields = ("personality",)
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ("id", "last_login", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "personality")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "name", "password1", "password2")}),
    )
