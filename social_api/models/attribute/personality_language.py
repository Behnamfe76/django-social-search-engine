from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class PersonalityLanguage(models.Model):
    pk = models.CompositePrimaryKey("personality_id", "language_id")
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.CASCADE,
        related_name="language_links",
    )
    language = models.ForeignKey(
        "Language",
        on_delete=models.CASCADE,
        related_name="personality_links",
    )
    proficiency = models.SmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="0-5",
    )

    class Meta:
        db_table = "personality_languages"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(proficiency__gte=0) & models.Q(proficiency__lte=5),
                name="personality_languages_proficiency_range",
            ),
        ]

    def __str__(self):
        return f"{self.personality_id}:{self.language_id}"
