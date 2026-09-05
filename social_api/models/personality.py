from django.db import models

from social_api.models.enums import GenderType


class Personality(models.Model):
    # re-exported so existing ``Personality.GenderType`` references keep working
    GenderType = GenderType

    id = models.AutoField(primary_key=True)
    external_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="linkedin_id from the source, falling back to linkedin_username.",
    )
    import_batch = models.ForeignKey(
        "ImportBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="personalities",
    )
    industry = models.ForeignKey(
        "Industry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="personalities",
    )
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, null=True, blank=True)
    middle_initial = models.CharField(max_length=1, null=True, blank=True)
    last_name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=512)
    gender = models.CharField(
        max_length=20,
        choices=GenderType.choices,
        default=GenderType.UNKNOWN,
    )
    birth_date = models.DateField(null=True, blank=True)
    birth_year = models.SmallIntegerField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    inferred_salary = models.CharField(max_length=100, null=True, blank=True)
    inferred_years_experience = models.SmallIntegerField(null=True, blank=True)
    version_status = models.JSONField(null=True, blank=True)
    location_last_updated = models.DateField(null=True, blank=True)
    locations = models.ManyToManyField(
        "Location",
        through="PersonalityLocation",
        related_name="personalities",
        blank=True,
    )
    skills = models.ManyToManyField(
        "Skill",
        through="PersonalitySkill",
        related_name="personalities",
        blank=True,
    )
    interests = models.ManyToManyField(
        "Interest",
        through="PersonalityInterest",
        related_name="personalities",
        blank=True,
    )
    languages = models.ManyToManyField(
        "Language",
        through="PersonalityLanguage",
        related_name="personalities",
        blank=True,
    )
    certifications = models.ManyToManyField(
        "Certification",
        through="PersonalityCertification",
        related_name="personalities",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "personalities"
        indexes = [
            models.Index(fields=["full_name"], name="personalities_full_name_idx"),
            models.Index(
                fields=["last_name", "first_name"],
                name="personalities_name_idx",
            ),
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        self.full_name = self.build_full_name()
        super().save(*args, **kwargs)

    def build_full_name(self):
        middle = self.middle_name or self.middle_initial
        return " ".join(
            part.strip()
            for part in [self.first_name, middle, self.last_name]
            if part and part.strip()
        )
