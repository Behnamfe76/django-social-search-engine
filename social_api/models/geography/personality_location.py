from django.db import models


class PersonalityLocation(models.Model):
    id = models.AutoField(primary_key=True)
    personality = models.ForeignKey(
        "Personality",
        on_delete=models.CASCADE,
        related_name="location_links",
    )
    location = models.ForeignKey(
        "Location",
        on_delete=models.CASCADE,
        related_name="personality_links",
    )
    street_address = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personality_locations"
        constraints = [
            # Re-importing a source file must not stack duplicate links.
            models.UniqueConstraint(
                fields=["personality", "location", "street_address"],
                name="personality_locations_uniq",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(
                fields=["personality", "location", "street_address"],
                name="personality_location_addr_idx",
            ),
            models.Index(
                fields=["personality", "location"],
                name="personality_location_idx",
            ),
        ]
