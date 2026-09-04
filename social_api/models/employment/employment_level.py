from django.db import models


class EmploymentLevel(models.Model):
    """Join table between an employment and the occupation levels it maps to."""

    pk = models.CompositePrimaryKey("employment_id", "occupation_level_id")
    employment = models.ForeignKey(
        "Employment",
        on_delete=models.CASCADE,
        related_name="level_links",
    )
    occupation_level_id = models.IntegerField()

    class Meta:
        db_table = "employment_levels"

    def __str__(self):
        return f"{self.employment_id}:{self.occupation_level_id}"
