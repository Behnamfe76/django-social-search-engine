from django.db import models


class OccupationSubRole(models.Model):
    id = models.AutoField(primary_key=True)
    occupation_role = models.ForeignKey(
        "OccupationRole",
        on_delete=models.CASCADE,
        related_name="sub_roles",
    )
    title = models.CharField(max_length=255)
    # Only unique within its parent role, not globally.
    slug = models.SlugField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "occupation_sub_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["occupation_role", "slug"],
                name="occupation_sub_roles_role_slug_uniq",
            ),
        ]

    def __str__(self):
        return self.title
