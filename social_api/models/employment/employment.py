from django.db import models


class Employment(models.Model):
    id = models.AutoField(primary_key=True)
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.CASCADE,
        related_name="employments",
    )
    company = models.ForeignKey(
        "Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employments",
    )
    occupation_id = models.IntegerField(null=True, blank=True)
    occupation_role_id = models.IntegerField(null=True, blank=True)
    occupation_sub_role_id = models.IntegerField(null=True, blank=True)
    location = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employments",
    )
    title = models.CharField(max_length=255, help_text="raw title as sourced")
    summary = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    last_updated = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employments"
        indexes = [
            models.Index(
                fields=["personality", "is_current"],
                name="employments_person_curr_idx",
            ),
            models.Index(fields=["company"], name="employments_company_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["personality", "company", "title", "start_date"],
                name="employments_person_co_title_start_uniq",
                nulls_distinct=False,
            ),
        ]

    def __str__(self):
        return f"{self.title} @ {self.company_id}"
