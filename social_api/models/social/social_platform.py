from django.db import models


class SocialPlatform(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    domain = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_platforms"
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="unique_social_platform_slug"),
        ]