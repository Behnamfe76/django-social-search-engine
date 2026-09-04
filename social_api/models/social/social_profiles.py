from django.db import models


class SocialProfiles(models.Model):
    id = models.AutoField(primary_key=True)
    social_platform = models.ForeignKey("SocialPlatform", on_delete=models.CASCADE)
    personality = models.ForeignKey("Personality", on_delete=models.CASCADE)
    platform_user_id = models.CharField(max_length=255, null=True, blank=True)
    user_name = models.CharField(max_length=255,  null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    connection_count = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["social_platform", "user_name"],
                name="unique_social_profile",
            ),
            models.UniqueConstraint(
                fields=["social_platform", "platform_user_id"],
                name="unique_social_platform",
            ),
        ]
