from django.db import models


class Location(models.Model):
    class LocationName(models.TextChoices):
        CITY = "City", "City"
        REGION = "Region", "Region"
        COUNTRY = "Country", "Country"

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=15,
        choices=LocationName.choices,
    )
    locality = models.CharField(max_length=126, null=True, blank=True)
    metro = models.CharField(max_length=126, null=True, blank=True)
    region = models.CharField(max_length=126, null=True, blank=True)
    country = models.CharField(max_length=126, null=True, blank=True)
    continent = models.CharField(max_length=126, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "locations"
        constraints = [
            models.UniqueConstraint(
                fields=["country", "region", "locality"],
                name="locations_country_region_locality_uniq",
                nulls_distinct=False,
            ),
        ]

    def __str__(self):
        return f"{self.name}: {self.locality}, {self.region}, {self.country}"
