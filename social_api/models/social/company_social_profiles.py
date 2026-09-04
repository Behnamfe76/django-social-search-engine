from django.db import models


class CompanySocialProfiles(models.Model):
    id = models.AutoField(primary_key=True)
    social_platform = models.ForeignKey("SocialPlatform", on_delete=models.CASCADE)
    company = models.ForeignKey("Company", on_delete=models.CASCADE)
    platform_user_id = models.CharField(max_length=255, null=True, blank=True)
    user_name = models.CharField(max_length=255,  null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_social_profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["social_platform", "company"],
                name="unique_company_social_profile",
            ),
        ]