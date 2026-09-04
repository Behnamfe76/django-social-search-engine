from django.db import models


class Company(models.Model):
    id = models.AutoField(primary_key=True)
    industry = models.ForeignKey(
        "Industry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="companies",
    )
    external_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="job_company_id from source",
    )
    location = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="companies",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    website = models.URLField(max_length=255, null=True, blank=True)
    size = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="bucket, e.g. 1001-5000",
    )
    founded_year = models.SmallIntegerField(null=True, blank=True)
    street_address = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        indexes = [
            models.Index(fields=["name"], name="companies_name_idx"),
            models.Index(fields=["website"], name="companies_website_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            from social_api.services.slug import build_unique_slug

            self.slug = build_unique_slug(
                self.name,
                model=Company,
                field_name="slug",
                max_length=255,
                fallback="company",
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
