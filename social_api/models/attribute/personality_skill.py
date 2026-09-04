from django.db import models


class PersonalitySkill(models.Model):
    pk = models.CompositePrimaryKey("personality_id", "skill_id")
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.CASCADE,
        related_name="skill_links",
    )
    skill = models.ForeignKey(
        "Skill",
        on_delete=models.CASCADE,
        related_name="personality_links",
    )

    class Meta:
        db_table = "personality_skills"

    def __str__(self):
        return f"{self.personality_id}:{self.skill_id}"
