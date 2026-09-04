from django.db import models


class Occupation(models.Model):
    id = models.AutoField(primary_key=True)
    industry = models.ForeignKey(
        "Industry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="occupations",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "occupations"

    def __str__(self):
        return self.title
