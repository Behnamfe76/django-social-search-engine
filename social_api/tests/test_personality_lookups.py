"""Lookup dimensions embedded in the profile payloads, and the filters that pair
with them.

The contract these tests pin down is that the two halves agree: an id read off a
profile's ``skills`` filters with ``?skill_id=``, and a lookup endpoint's
``count`` equals the number of profiles that filter returns.
"""

from django.contrib.auth import get_user_model
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework import status
from rest_framework.test import APITestCase

from social_api.models import (
    Certification,
    Company,
    Employment,
    EmploymentLevel,
    Industry,
    Interest,
    Language,
    OccupationLevel,
    OccupationRole,
    Personality,
    PersonalityCertification,
    PersonalityInterest,
    PersonalityLanguage,
    PersonalitySkill,
    Skill,
)
from social_api.selectors.lookup import lookup_queryset
from social_api.tests.support import authenticate

LOOKUP_COLLECTIONS = [
    "skills",
    "interests",
    "languages",
    "certifications",
    "companies",
    "occupation_roles",
    "occupation_levels",
]


class PersonalityLookupTestCase(APITestCase):
    def setUp(self):
        authenticate(
            self.client,
            get_user_model().objects.create_user(
                email="lookups@example.com", password="pw", name="Lookups"
            ),
        )
        self.industry = Industry.objects.create(name="Software", slug="software")
        self.ada = Personality.objects.create(
            first_name="ada", last_name="lovelace", industry=self.industry
        )

        self.python = Skill.objects.create(name="python", slug="python")
        self.rust = Skill.objects.create(name="rust", slug="rust")
        PersonalitySkill.objects.create(personality=self.ada, skill=self.python)
        PersonalitySkill.objects.create(personality=self.ada, skill=self.rust)

        self.chess = Interest.objects.create(name="chess", slug="chess")
        PersonalityInterest.objects.create(personality=self.ada, interest=self.chess)

        self.english = Language.objects.create(name="english", slug="english")
        PersonalityLanguage.objects.create(personality=self.ada, language=self.english)

        self.cert = Certification.objects.create(name="csm", slug="csm")
        PersonalityCertification.objects.create(
            personality=self.ada, certification=self.cert
        )

        self.company = Company.objects.create(name="Analytical", slug="analytical")
        self.role = OccupationRole.objects.create(title="engineering", slug="eng")
        self.level = OccupationLevel.objects.create(title="senior", slug="senior")
        self.job = Employment.objects.create(
            personality=self.ada,
            company=self.company,
            occupation_role=self.role,
            title="engineer",
            start_date="2010-01-01",
        )
        EmploymentLevel.objects.create(
            employment=self.job, occupation_level=self.level
        )

    def list_rows(self, query=""):
        response = self.client.get(f"/api/v1/personalities/{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["results"]

    def ada_row(self):
        return next(row for row in self.list_rows() if row["id"] == self.ada.pk)


class EmbeddedLookupTests(PersonalityLookupTestCase):
    def test_list_embeds_every_lookup_collection(self):
        row = self.ada_row()

        for field in LOOKUP_COLLECTIONS:
            with self.subTest(field=field):
                self.assertIn(field, row)

    def test_detail_embeds_every_lookup_collection(self):
        response = self.client.get(f"/api/v1/personalities/{self.ada.pk}/")

        for field in LOOKUP_COLLECTIONS:
            with self.subTest(field=field):
                self.assertIn(field, response.data)

    def test_entries_carry_the_id_and_the_label(self):
        row = self.ada_row()

        self.assertEqual(
            sorted(row["skills"], key=lambda item: item["name"]),
            [
                {"id": self.python.pk, "name": "python"},
                {"id": self.rust.pk, "name": "rust"},
            ],
        )

    def test_employment_derived_collections_are_flattened(self):
        """companies / roles / levels hang off employments, not off the profile."""
        row = self.ada_row()

        self.assertEqual(
            row["companies"], [{"id": self.company.pk, "name": "Analytical"}]
        )
        self.assertEqual(
            row["occupation_roles"], [{"id": self.role.pk, "name": "engineering"}]
        )
        self.assertEqual(
            row["occupation_levels"], [{"id": self.level.pk, "name": "senior"}]
        )

    def test_repeated_employers_appear_once(self):
        Employment.objects.create(
            personality=self.ada,
            company=self.company,
            occupation_role=self.role,
            title="senior engineer",
            start_date="2015-01-01",
        )

        row = self.ada_row()

        self.assertEqual(len(row["companies"]), 1)
        self.assertEqual(len(row["occupation_roles"]), 1)

    def test_a_profile_with_nothing_attached_gets_empty_lists(self):
        Personality.objects.create(first_name="alan", last_name="turing")

        row = next(
            item for item in self.list_rows() if item["full_name"] == "alan turing"
        )

        for field in LOOKUP_COLLECTIONS:
            with self.subTest(field=field):
                self.assertEqual(row[field], [])

    def test_detail_carries_the_industry_label_beside_the_writable_id(self):
        response = self.client.get(f"/api/v1/personalities/{self.ada.pk}/")

        self.assertEqual(response.data["industry_id"], self.industry.pk)
        self.assertEqual(response.data["industry"], "Software")

    def test_write_serializers_do_not_expose_the_collections(self):
        """Create and update stay writable payloads, not read projections."""
        response = self.client.post(
            "/api/v1/personalities/",
            {"first_name": "grace", "last_name": "hopper"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for field in LOOKUP_COLLECTIONS:
            with self.subTest(field=field):
                self.assertNotIn(field, response.data)


class EmbeddedLookupQueryCountTests(PersonalityLookupTestCase):
    def test_query_count_does_not_grow_with_the_page(self):
        """The collections are prefetched; a wider page must not cost more queries."""
        with CaptureQueriesContext(connection) as one_profile:
            self.client.get("/api/v1/personalities/")

        for index in range(10):
            person = Personality.objects.create(
                first_name=f"person{index}", last_name="extra", industry=self.industry
            )
            PersonalitySkill.objects.create(personality=person, skill=self.python)
            job = Employment.objects.create(
                personality=person,
                company=self.company,
                occupation_role=self.role,
                title="engineer",
                start_date="2012-01-01",
            )
            EmploymentLevel.objects.create(
                employment=job, occupation_level=self.level
            )

        with CaptureQueriesContext(connection) as many_profiles:
            response = self.client.get("/api/v1/personalities/")

        self.assertEqual(len(response.data["results"]), 11)
        self.assertEqual(len(many_profiles), len(one_profile))


class LookupFilterTests(PersonalityLookupTestCase):
    def setUp(self):
        super().setUp()
        # A second profile sharing nothing with the first, so every filter has
        # something to exclude.
        self.alan = Personality.objects.create(first_name="alan", last_name="turing")
        self.haskell = Skill.objects.create(name="haskell", slug="haskell")
        PersonalitySkill.objects.create(personality=self.alan, skill=self.haskell)

    def ids_for(self, query):
        return [row["id"] for row in self.list_rows(query)]

    def test_every_lookup_has_a_matching_filter(self):
        cases = [
            (f"?industry_id={self.industry.pk}", self.ada),
            (f"?skill_id={self.python.pk}", self.ada),
            (f"?interest_id={self.chess.pk}", self.ada),
            (f"?language_id={self.english.pk}", self.ada),
            (f"?certification_id={self.cert.pk}", self.ada),
            (f"?company_id={self.company.pk}", self.ada),
            (f"?occupation_role_id={self.role.pk}", self.ada),
            (f"?occupation_level_id={self.level.pk}", self.ada),
            (f"?skill_id={self.haskell.pk}", self.alan),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(self.ids_for(query), [expected.pk])

    def test_repeating_a_parameter_ors_the_values(self):
        query = f"?skill_id={self.python.pk}&skill_id={self.haskell.pk}"

        self.assertEqual(sorted(self.ids_for(query)), sorted([self.ada.pk, self.alan.pk]))

    def test_matching_several_values_does_not_duplicate_the_profile(self):
        """Filtering across a to-many relation needs DISTINCT."""
        query = f"?skill_id={self.python.pk}&skill_id={self.rust.pk}"

        ids = self.ids_for(query)

        self.assertEqual(ids, [self.ada.pk])

    def test_several_employments_matching_one_company_yields_one_row(self):
        Employment.objects.create(
            personality=self.ada,
            company=self.company,
            title="second stint",
            start_date="2015-01-01",
        )

        self.assertEqual(self.ids_for(f"?company_id={self.company.pk}"), [self.ada.pk])

    def test_filters_combine(self):
        self.assertEqual(
            self.ids_for(f"?skill_id={self.python.pk}&gender=unknown"), [self.ada.pk]
        )
        self.assertEqual(
            self.ids_for(f"?skill_id={self.python.pk}&gender=female"), []
        )

    def test_an_unknown_id_is_rejected(self):
        response = self.client.get("/api/v1/personalities/?skill_id=999999")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("skill_id", response.data)

    def test_soft_deleted_profiles_stay_out_of_filtered_results(self):
        from django.utils import timezone

        self.ada.deleted_at = timezone.now()
        self.ada.save(update_fields=["deleted_at"])

        self.assertEqual(self.ids_for(f"?skill_id={self.python.pk}"), [])


class LookupCountMatchesFilterTests(PersonalityLookupTestCase):
    """A lookup's ``count`` is a promise about what filtering by it returns."""

    CASES = [
        (Industry, "industry_id"),
        (Skill, "skill_id"),
        (Interest, "interest_id"),
        (Language, "language_id"),
        (Certification, "certification_id"),
        (Company, "company_id"),
        (OccupationRole, "occupation_role_id"),
        (OccupationLevel, "occupation_level_id"),
    ]

    def test_advertised_count_equals_the_filtered_result_count(self):
        for model, parameter in self.CASES:
            for option in lookup_queryset(model):
                with self.subTest(model=model.__name__, option=option.pk):
                    response = self.client.get(
                        f"/api/v1/personalities/?{parameter}={option.pk}"
                    )
                    self.assertEqual(response.data["count"], option.count)
