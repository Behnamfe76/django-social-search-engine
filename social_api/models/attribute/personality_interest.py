from django.db import models


class PersonalityInterest(models.Model):
    pk = models.CompositePrimaryKey("personality_id", "interest_id")
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.CASCADE,
        related_name="interest_links",
    )
    interest = models.ForeignKey(
        "Interest",
        on_delete=models.CASCADE,
        related_name="personality_links",
    )

    class Meta:
        db_table = "personality_interests"

    def __str__(self):
        return f"{self.personality_id}:{self.interest_id}"
