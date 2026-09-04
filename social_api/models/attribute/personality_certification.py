from django.db import models


class PersonalityCertification(models.Model):
    id = models.AutoField(primary_key=True)
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.CASCADE,
        related_name="certification_links",
    )
    certification = models.ForeignKey(
        "Certification",
        on_delete=models.CASCADE,
        related_name="personality_links",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personality_certifications"
        constraints = [
            models.UniqueConstraint(
                fields=["personality", "certification", "start_date"],
                name="personality_certifications_uniq",
                nulls_distinct=False,
            ),
        ]

    def __str__(self):
        return f"{self.personality_id}:{self.certification_id}"
