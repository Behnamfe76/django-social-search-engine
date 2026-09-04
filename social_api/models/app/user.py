from django.db import models


class User(models.Model):
    """Application user.

    This is a plain model, not ``AUTH_USER_MODEL`` - ``django.contrib.auth`` still
    backs admin login. See the note in the review before wiring authentication to it.
    """

    id = models.AutoField(primary_key=True)
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="optional self-link",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email
