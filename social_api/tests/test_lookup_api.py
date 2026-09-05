"""Filter-options endpoints: cursor-paged reference lists, 25 to a page."""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from social_api.models import (
    Certification,
    Company,
    Employment,
    Industry,
    OccupationRole,
    Personality,
    PersonalitySkill,
    Skill,
)
from social_api.tests.support import authenticate

PAGE_SIZE = 25

LOOKUP_PATHS = [
    "/api/v1/industries/",
    "/api/v1/skills/",
    "/api/v1/interests/",
    "/api/v1/languages/",
    "/api/v1/certifications/",
    "/api/v1/companies/",
    "/api/v1/occupation-roles/",
    "/api/v1/occupation-levels/",
]


class LookupTestCase(APITestCase):
    def setUp(self):
        authenticate(
            self.client,
            get_user_model().objects.create_user(
                email="lookup@example.com", password="pw", name="Lookup"
            ),
        )

    def walk(self, path):
        """Follow every cursor to the end, returning the rows in order."""
        rows = []
        url = path
        for _ in range(200):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            rows.extend(response.data["results"])
            url = response.data["next"]
            if url is None:
                return rows
        self.fail("cursor did not terminate")


class LookupAuthTests(APITestCase):
    def test_every_lookup_requires_a_token(self):
        for path in LOOKUP_PATHS:
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(path).status_code, status.HTTP_401_UNAUTHORIZED
                )


class LookupShapeTests(LookupTestCase):
    def test_every_lookup_answers_with_the_same_row_shape(self):
        Industry.objects.create(name="Software", slug="software")
        Skill.objects.create(name="python", slug="python")
        OccupationRole.objects.create(title="engineering", slug="engineering")

        for path in LOOKUP_PATHS:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    sorted(response.data), ["next", "previous", "results"]
                )
                for row in response.data["results"]:
                    self.assertEqual(sorted(row), ["count", "id", "name"])

    def test_title_backed_lookups_still_expose_name(self):
        """``OccupationRole`` stores its label in ``title``; the API says ``name``."""
        OccupationRole.objects.create(title="engineering", slug="engineering")

        row = self.client.get("/api/v1/occupation-roles/").data["results"][0]

        self.assertEqual(row["name"], "engineering")

    def test_cursor_pagination_reports_no_total_count(self):
        """A keyset cursor deliberately cannot know how many rows follow."""
        Industry.objects.create(name="Software", slug="software")

        self.assertNotIn("count", self.client.get("/api/v1/industries/").data)

    def test_retrieve_resolves_a_single_option(self):
        industry = Industry.objects.create(name="Software", slug="software")

        response = self.client.get(f"/api/v1/industries/{industry.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"id": industry.pk, "name": "Software", "count": 0}
        )


class LookupPaginationTests(LookupTestCase):
    def setUp(self):
        super().setUp()
        Industry.objects.bulk_create(
            Industry(name=f"industry {index:03}", slug=f"industry-{index:03}")
            for index in range(60)
        )

    def test_page_holds_twenty_five_rows(self):
        response = self.client.get("/api/v1/industries/")

        self.assertEqual(len(response.data["results"]), PAGE_SIZE)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_walking_the_cursor_visits_every_row_exactly_once(self):
        rows = self.walk("/api/v1/industries/")

        ids = [row["id"] for row in rows]
        self.assertEqual(len(ids), 60)
        self.assertEqual(len(set(ids)), 60)

    def test_rows_come_back_in_name_order(self):
        names = [row["name"] for row in self.walk("/api/v1/industries/")]

        self.assertEqual(names, sorted(names))

    def test_previous_cursor_returns_the_earlier_page(self):
        first = self.client.get("/api/v1/industries/").data
        second = self.client.get(first["next"]).data

        back = self.client.get(second["previous"]).data

        self.assertEqual(
            [row["id"] for row in back["results"]],
            [row["id"] for row in first["results"]],
        )

    def test_duplicate_names_do_not_break_the_cursor(self):
        """``name`` carries no unique constraint, so ties must page cleanly.

        DRF seeks with a strict ``name__gt`` and walks equal names with an
        offset; without the ``pk`` tie-break in the ordering a run of identical
        names straddling a page boundary can drop or repeat rows.
        """
        Industry.objects.all().delete()
        Industry.objects.bulk_create(
            Industry(name="duplicate", slug=f"duplicate-{index:03}")
            for index in range(60)
        )

        ids = [row["id"] for row in self.walk("/api/v1/industries/")]

        self.assertEqual(len(ids), 60)
        self.assertEqual(len(set(ids)), 60)

    def test_client_supplied_ordering_is_ignored(self):
        """Re-sorting under a cursor would make its position meaningless."""
        plain = self.client.get("/api/v1/industries/").data["results"]
        reordered = self.client.get(
            "/api/v1/industries/", {"ordering": "-name"}
        ).data["results"]

        self.assertEqual(plain, reordered)


class LookupSearchTests(LookupTestCase):
    def setUp(self):
        super().setUp()
        Industry.objects.create(name="computer software", slug="computer-software")
        Industry.objects.create(name="financial services", slug="financial-services")
        Industry.objects.create(name="software engineering", slug="software-eng")

    def test_search_narrows_the_options(self):
        response = self.client.get("/api/v1/industries/", {"search": "software"})

        names = sorted(row["name"] for row in response.data["results"])
        self.assertEqual(names, ["computer software", "software engineering"])

    def test_search_is_case_insensitive(self):
        response = self.client.get("/api/v1/industries/", {"search": "SOFTware"})

        names = sorted(row["name"] for row in response.data["results"])
        self.assertEqual(names, ["computer software", "software engineering"])

    def test_search_matches_anywhere_in_the_name(self):
        """A prefix-only match would miss "us army" for "army"."""
        response = self.client.get("/api/v1/industries/", {"search": "services"})

        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["financial services"])

    def test_search_finds_nothing_gracefully(self):
        response = self.client.get("/api/v1/industries/", {"search": "nothing here"})

        self.assertEqual(response.data["results"], [])
        self.assertIsNone(response.data["next"])

    def test_search_results_page_with_a_cursor(self):
        """Search narrows before paging, so a wide match still pages 25 at a time."""
        Industry.objects.bulk_create(
            Industry(name=f"software {index:03}", slug=f"software-{index:03}")
            for index in range(40)
        )

        first = self.client.get("/api/v1/industries/", {"search": "software"}).data
        self.assertEqual(len(first["results"]), PAGE_SIZE)
        self.assertIsNotNone(first["next"])

        rows = self.walk("/api/v1/industries/?search=software")
        ids = [row["id"] for row in rows]

        # 40 generated + "computer software" + "software engineering"
        self.assertEqual(len(ids), 42)
        self.assertEqual(len(set(ids)), 42)
        for row in rows:
            self.assertIn("software", row["name"])

    def test_search_works_on_title_backed_lookups(self):
        """``OccupationRole`` searches ``title`` while the API calls it ``name``."""
        OccupationRole.objects.create(title="engineering", slug="engineering")
        OccupationRole.objects.create(title="operations", slug="operations")

        response = self.client.get("/api/v1/occupation-roles/", {"search": "ENGIN"})

        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["engineering"])

    def test_certifications_also_search_the_issuing_organization(self):
        Certification.objects.create(
            name="azure fundamentals", slug="az-900", organization="Microsoft"
        )
        Certification.objects.create(
            name="certified scrum master", slug="csm", organization="Scrum Alliance"
        )

        response = self.client.get("/api/v1/certifications/", {"search": "microsoft"})

        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["azure fundamentals"])


class LookupCountTests(LookupTestCase):
    def setUp(self):
        super().setUp()
        self.industry = Industry.objects.create(name="Software", slug="software")
        self.ada = Personality.objects.create(
            first_name="ada", last_name="lovelace", industry=self.industry
        )
        self.alan = Personality.objects.create(
            first_name="alan", last_name="turing", industry=self.industry
        )

    def industry_row(self):
        return self.client.get("/api/v1/industries/").data["results"][0]

    def test_count_is_the_number_of_matching_profiles(self):
        self.assertEqual(self.industry_row()["count"], 2)

    def test_count_excludes_soft_deleted_profiles(self):
        """The count promises what filtering by this option would return."""
        self.alan.deleted_at = timezone.now()
        self.alan.save(update_fields=["deleted_at"])

        self.assertEqual(self.industry_row()["count"], 1)

    def test_options_with_no_profiles_are_still_listed_with_zero(self):
        Industry.objects.create(name="Aviation", slug="aviation")

        rows = {row["name"]: row["count"] for row in self.walk("/api/v1/industries/")}

        self.assertEqual(rows["Aviation"], 0)

    def test_skill_count_counts_people_not_link_rows(self):
        skill = Skill.objects.create(name="python", slug="python")
        PersonalitySkill.objects.create(personality=self.ada, skill=skill)
        PersonalitySkill.objects.create(personality=self.alan, skill=skill)

        row = self.client.get("/api/v1/skills/").data["results"][0]

        self.assertEqual(row["count"], 2)

    def test_company_count_counts_people_not_employments(self):
        """Two stints at one employer is one person for filtering purposes."""
        company = Company.objects.create(name="Navy", slug="navy")
        Employment.objects.create(
            personality=self.ada, company=company, title="a", start_date="2010-01-01"
        )
        Employment.objects.create(
            personality=self.ada, company=company, title="b", start_date="2015-01-01"
        )

        row = self.client.get("/api/v1/companies/").data["results"][0]

        self.assertEqual(row["count"], 1)
