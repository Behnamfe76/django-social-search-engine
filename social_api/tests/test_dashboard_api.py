"""The dashboard endpoint: one unfiltered snapshot, so the tests pin the shape
and the arithmetic rather than any query-parameter behaviour."""

from datetime import date

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from social_api.models import (
    Company,
    Employment,
    EmploymentLevel,
    ImportBatch,
    OccupationLevel,
    OccupationRole,
    Personality,
    PersonalitySkill,
    Skill,
    SocialPlatform,
    SocialProfiles,
)
from social_api.selectors.dashboard import COMPANY_SIZE_BUCKETS, dashboard_stats
from social_api.tests.support import authenticate

URL = "/api/v1/dashboard/"

PANELS = [
    "totals",
    "gender",
    "top_skills",
    "top_interests",
    "top_languages",
    "top_certifications",
    "top_companies",
    "company_sizes",
    "occupation_roles",
    "seniority_levels",
    "seniority_by_role",
    "tenure",
    "employment_status",
    "employments_per_person",
    "hires_by_year",
    "social_platforms",
    "platform_reach",
    "coverage",
    "imports",
]


def person(first, last, **overrides):
    return Personality.objects.create(
        first_name=first, last_name=last, **overrides
    )


class DashboardAuthTests(APITestCase):
    def test_requires_a_token(self):
        self.assertEqual(
            self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_returns_a_snapshot_to_an_authenticated_caller(self):
        authenticate(
            self.client,
            get_user_model().objects.create_user(
                email="dash@example.com", password="pw", name="Dash"
            ),
        )

        response = self.client.get(URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data), sorted(PANELS))


class DashboardShapeTests(APITestCase):
    """An empty database must still answer with every panel present."""

    def test_empty_database_yields_every_panel(self):
        stats = dashboard_stats()

        self.assertEqual(sorted(stats), sorted(PANELS))
        self.assertEqual(stats["totals"]["personalities"], 0)
        self.assertEqual(stats["gender"], [])
        self.assertEqual(stats["coverage"], [])
        self.assertIsNone(stats["tenure"]["median_years"])
        self.assertEqual(stats["tenure"]["sample_size"], 0)

    def test_company_size_buckets_are_fixed_and_ordered(self):
        """Junk sizes are dropped and empty buckets still hold their slot."""
        Company.objects.create(name="Big", slug="big", size="10001+")
        Company.objects.create(name="Small", slug="small", size="1-10")
        Company.objects.create(name="Junk", slug="junk", size="united states")

        buckets = dashboard_stats()["company_sizes"]

        self.assertEqual([b["name"] for b in buckets], COMPANY_SIZE_BUCKETS)
        by_name = {b["name"]: b["count"] for b in buckets}
        self.assertEqual(by_name["10001+"], 1)
        self.assertEqual(by_name["1-10"], 1)
        self.assertEqual(by_name["51-200"], 0)
        self.assertNotIn("united states", by_name)


class DashboardCountingTests(APITestCase):
    def setUp(self):
        self.ada = person("ada", "lovelace", gender="female")
        self.alan = person("alan", "turing", gender="male")
        self.skill = Skill.objects.create(name="python", slug="python")
        PersonalitySkill.objects.create(personality=self.ada, skill=self.skill)
        PersonalitySkill.objects.create(personality=self.alan, skill=self.skill)

    def test_soft_deleted_profiles_are_excluded(self):
        self.alan.deleted_at = timezone.now()
        self.alan.save(update_fields=["deleted_at"])

        stats = dashboard_stats()

        self.assertEqual(stats["totals"]["personalities"], 1)
        self.assertEqual(stats["gender"], [{"name": "female", "count": 1}])
        self.assertEqual(stats["top_skills"], [{"name": "python", "count": 1}])

    def test_top_skills_counts_people_not_link_rows(self):
        """The join tables use composite keys, so this is easy to get wrong."""
        stats = dashboard_stats()

        self.assertEqual(stats["top_skills"], [{"name": "python", "count": 2}])

    def test_gender_split_covers_every_profile(self):
        stats = dashboard_stats()

        self.assertEqual(
            sum(row["count"] for row in stats["gender"]),
            stats["totals"]["personalities"],
        )

    def test_coverage_reports_fill_rate(self):
        self.ada.summary = "Mathematician."
        self.ada.save(update_fields=["summary"])

        coverage = {row["name"]: row for row in dashboard_stats()["coverage"]}

        self.assertEqual(coverage["summary"]["filled"], 1)
        self.assertEqual(coverage["summary"]["total"], 2)
        self.assertEqual(coverage["summary"]["percent"], 50.0)


class DashboardEmploymentTests(APITestCase):
    def setUp(self):
        self.person = person("grace", "hopper")
        self.company = Company.objects.create(
            name="Navy", slug="navy", size="10001+"
        )
        self.role = OccupationRole.objects.create(title="engineering", slug="eng")
        self.level = OccupationLevel.objects.create(title="director", slug="director")

    def employment(self, title, start, end, **overrides):
        return Employment.objects.create(
            personality=self.person,
            company=self.company,
            title=title,
            start_date=start,
            end_date=end,
            **overrides,
        )

    def test_tenure_summarises_completed_stints_only(self):
        self.employment("a", date(2010, 1, 1), date(2012, 1, 1))  # 2.0 years
        self.employment("b", date(2015, 1, 1), date(2019, 1, 1))  # 4.0 years
        self.employment("open", date(2020, 1, 1), None, is_current=True)

        tenure = dashboard_stats()["tenure"]

        self.assertEqual(tenure["sample_size"], 2)
        self.assertEqual(tenure["median_years"], 3.0)
        self.assertEqual(tenure["mean_years"], 3.0)

    def test_tenure_buckets_partition_the_sample(self):
        self.employment("short", date(2010, 1, 1), date(2010, 6, 1))
        self.employment("mid", date(2011, 1, 1), date(2014, 1, 1))
        self.employment("long", date(2000, 1, 1), date(2015, 1, 1))

        tenure = dashboard_stats()["tenure"]
        by_name = {b["name"]: b["count"] for b in tenure["buckets"]}

        self.assertEqual(sum(by_name.values()), tenure["sample_size"])
        self.assertEqual(by_name["under 1 year"], 1)
        self.assertEqual(by_name["2-5 years"], 1)
        self.assertEqual(by_name["10+ years"], 1)

    def test_employment_status_splits_current_from_past(self):
        self.employment("now", date(2020, 1, 1), None, is_current=True)
        self.employment("then", date(2010, 1, 1), date(2012, 1, 1))

        self.assertEqual(
            dashboard_stats()["employment_status"],
            [{"name": "current", "count": 1}, {"name": "past", "count": 1}],
        )

    def test_hires_by_year_uses_start_dates_not_import_time(self):
        self.employment("a", date(2011, 3, 1), date(2012, 1, 1))
        self.employment("b", date(2011, 9, 1), date(2013, 1, 1))
        self.employment("c", date(2014, 1, 1), None)

        self.assertEqual(
            dashboard_stats()["hires_by_year"],
            [{"year": 2011, "count": 2}, {"year": 2014, "count": 1}],
        )

    def test_employments_per_person_is_a_histogram(self):
        self.employment("a", date(2011, 1, 1), date(2012, 1, 1))
        self.employment("b", date(2012, 1, 1), date(2013, 1, 1))
        person("solo", "profile")  # nobody's employer

        histogram = dashboard_stats()["employments_per_person"]

        self.assertEqual(
            histogram, [{"employments": 0, "people": 1}, {"employments": 2, "people": 1}]
        )

    def test_seniority_by_role_cross_tabulates(self):
        job = self.employment(
            "lead", date(2011, 1, 1), None, occupation_role=self.role
        )
        EmploymentLevel.objects.create(employment=job, occupation_level=self.level)

        self.assertEqual(
            dashboard_stats()["seniority_by_role"],
            [{"role": "engineering", "level": "director", "count": 1}],
        )

    def test_seniority_levels_lists_the_whole_taxonomy(self):
        OccupationLevel.objects.create(title="entry", slug="entry")

        levels = dashboard_stats()["seniority_levels"]

        self.assertEqual({row["name"] for row in levels}, {"director", "entry"})


class DashboardSocialTests(APITestCase):
    def setUp(self):
        self.person = person("ada", "lovelace")
        self.linkedin = SocialPlatform.objects.create(
            name="LinkedIn", slug="linkedin", domain="linkedin.com"
        )
        self.github = SocialPlatform.objects.create(
            name="GitHub", slug="github", domain="github.com"
        )

    def test_platform_counts_and_reach(self):
        SocialProfiles.objects.create(
            social_platform=self.linkedin, personality=self.person, user_name="ada"
        )
        SocialProfiles.objects.create(
            social_platform=self.github, personality=self.person, user_name="ada-gh"
        )
        person("alan", "turing")  # on no platform at all

        stats = dashboard_stats()

        self.assertEqual(
            stats["social_platforms"],
            [
                {"name": "github", "profiles": 1, "people": 1},
                {"name": "linkedin", "profiles": 1, "people": 1},
            ],
        )
        self.assertEqual(
            stats["platform_reach"],
            [{"platforms": 0, "people": 1}, {"platforms": 2, "people": 1}],
        )


class DashboardImportsTests(APITestCase):
    def test_import_counters_are_rolled_up(self):
        ImportBatch.objects.create(
            source="pdl",
            filename="a.csv",
            status=ImportBatch.Status.COMPLETED,
            processed_rows=100,
            created_rows=90,
            updated_rows=10,
            failed_rows=0,
        )
        ImportBatch.objects.create(
            source="pdl",
            filename="b.csv",
            status=ImportBatch.Status.PARTIAL,
            processed_rows=50,
            created_rows=40,
            updated_rows=5,
            failed_rows=5,
        )

        imports = dashboard_stats()["imports"]

        self.assertEqual(imports["processed_rows"], 150)
        self.assertEqual(imports["created_rows"], 130)
        self.assertEqual(imports["updated_rows"], 15)
        self.assertEqual(imports["failed_rows"], 5)
        self.assertEqual(
            sorted(imports["batches"], key=lambda row: row["name"]),
            [{"name": "completed", "count": 1}, {"name": "partial", "count": 1}],
        )


class DashboardNoFilteringTests(APITestCase):
    """The endpoint takes no parameters; stray ones must not change the answer."""

    def setUp(self):
        authenticate(
            self.client,
            get_user_model().objects.create_user(
                email="dash@example.com", password="pw", name="Dash"
            ),
        )
        person("ada", "lovelace", gender="female")
        person("alan", "turing", gender="male")

    def test_query_parameters_are_ignored(self):
        plain = self.client.get(URL).data
        filtered = self.client.get(
            URL, {"gender": "male", "ordering": "-id", "page": 2}
        ).data

        self.assertEqual(plain, filtered)

    def test_response_is_not_paginated(self):
        response = self.client.get(URL)

        self.assertNotIn("results", response.data)
        self.assertNotIn("count", response.data)
