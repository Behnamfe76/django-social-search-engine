from django.db import models


class Personality(models.Model):
    class GenderType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        NON_BINARY = "non_binary", "Non-binary"
        OTHER = "other", "Other"

    id = models.AutoField(primary_key=True)
    import_batch_id = models.IntegerField(null=True, blank=True)
    industry_id = models.IntegerField(null=True, blank=True)
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
            models.Index(fields=["industry_id"], name="personalities_industry_idx"),
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
