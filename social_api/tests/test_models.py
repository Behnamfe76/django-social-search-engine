import unittest

from django.test import TestCase

from social_api.models import Company, Employment, EmploymentLevel, Personality
from social_api.tests.support import tables_exist


@unittest.skipUnless(
    tables_exist("companies", "employments", "employment_levels"),
    "employment tables have no migration yet",
)
class EmploymentModelTests(TestCase):
    def setUp(self):
        self.personality = Personality.objects.create(first_name="Ada", last_name="Lovelace")
        self.company = Company.objects.create(
            name="Analytical Engines",
            slug="analytical-engines",
        )

    def test_employment_links_personality_and_company(self):
        employment = Employment.objects.create(
            personality=self.personality,
            company=self.company,
            title="Mathematician",
            is_current=True,
        )

        self.assertEqual(self.personality.employments.get(), employment)
        self.assertEqual(self.company.employments.get(), employment)

    def test_employment_level_uses_composite_primary_key(self):
        employment = Employment.objects.create(
            personality=self.personality,
            title="Mathematician",
        )
        level = EmploymentLevel.objects.create(employment=employment, occupation_level_id=3)

        self.assertEqual(level.pk, (employment.pk, 3))
        self.assertEqual(employment.level_links.count(), 1)
