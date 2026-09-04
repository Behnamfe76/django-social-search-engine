from django.db import IntegrityError, transaction
from django.test import TestCase

from social_api.models import (
    Company,
    Employment,
    EmploymentLevel,
    Industry,
    Occupation,
    OccupationLevel,
    OccupationRole,
    OccupationSubRole,
    Personality,
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
        level = OccupationLevel.objects.create(title="Senior", slug="senior")
        link = EmploymentLevel.objects.create(employment=employment, occupation_level=level)

        self.assertEqual(link.pk, (employment.pk, level.pk))
        self.assertEqual(employment.level_links.count(), 1)
        self.assertEqual(level.employment_links.get(), link)

    def test_employment_links_the_occupation_taxonomy(self):
        industry = Industry.objects.create(name="Software", slug="software")
        occupation = Occupation.objects.create(
            industry=industry, title="Engineer", slug="engineer"
        )
        role = OccupationRole.objects.create(title="Engineering", slug="engineering")
        sub_role = OccupationSubRole.objects.create(
            occupation_role=role, title="Backend", slug="backend"
        )

        employment = Employment.objects.create(
            personality=self.personality,
            company=self.company,
            title="Backend Engineer",
            occupation=occupation,
            occupation_role=role,
            occupation_sub_role=sub_role,
        )

        self.assertEqual(occupation.employments.get(), employment)
        self.assertEqual(role.employments.get(), employment)
        self.assertEqual(sub_role.employments.get(), employment)
        self.assertEqual(industry.occupations.get(), occupation)
        self.assertEqual(role.sub_roles.get(), sub_role)


class OccupationTaxonomyTests(TestCase):
    def test_industry_links_companies_and_personalities(self):
        industry = Industry.objects.create(name="Software", slug="software")
        company = Company.objects.create(name="Acme", slug="acme", industry=industry)
        person = Personality.objects.create(
            first_name="Ada", last_name="Lovelace", industry=industry
        )

        self.assertEqual(industry.companies.get(), company)
        self.assertEqual(industry.personalities.get(), person)

    def test_sub_role_slug_is_unique_per_role_not_globally(self):
        role_a = OccupationRole.objects.create(title="Engineering", slug="engineering")
        role_b = OccupationRole.objects.create(title="Design", slug="design")

        OccupationSubRole.objects.create(occupation_role=role_a, title="Lead", slug="lead")
        # same slug under a different role is allowed
        OccupationSubRole.objects.create(occupation_role=role_b, title="Lead", slug="lead")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OccupationSubRole.objects.create(
                    occupation_role=role_a, title="Lead again", slug="lead"
                )

    def test_slugs_are_globally_unique_where_declared(self):
        Industry.objects.create(name="Software", slug="software")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Industry.objects.create(name="Software Services", slug="software")
