"""Shared test helpers."""

import csv
import io
import tempfile

from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken


def access_token(user):
    return str(RefreshToken.for_user(user).access_token)


def authenticate(client, user):
    """Attach a real Bearer token to an APIClient.

    ``force_authenticate`` is not enough here: JWTRouteAuthMiddleware runs before
    the view and would reject the request before DRF ever sees it.
    """
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token(user)}")
    return client


class EagerCeleryMixin:
    """Run tasks inline instead of putting them on the broker.

    The app is configured with ``config_from_object("django.conf:settings")``, and
    that live mapping sits above any direct ``app.conf`` assignment in Celery's
    config chain -- so the Django setting is the only handle that actually works.
    """

    def setUp(self):
        super().setUp()
        override = override_settings(
            CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True
        )
        override.enable()
        self.addCleanup(override.disable)


class TemporaryMediaMixin:
    """Keep uploaded fixtures out of the project's media directory."""

    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.media_root = directory.name


# -- CSV fixtures ---------------------------------------------------------

PROFILE_COLUMNS = [
    "linkedin_id",
    "linkedin_username",
    "linkedin_url",
    "first_name",
    "last_name",
    "full_name",
    "gender",
    "industry",
    "summary",
    "birth_year",
    "inferred_years_experience",
    "linkedin_connections",
    "skills",
    "interests",
    "languages",
    "certifications",
    "experience",
    "profiles",
    "location_locality",
    "location_region",
    "location_country",
    "location_geo",
    "location_street_address",
    "location_postal_code",
    "job_title",
    "job_title_role",
    "job_title_sub_role",
    "job_title_levels",
    "job_company_id",
    "job_company_name",
    "job_start_date",
    "job_last_updated",
]

EXPERIENCE = [
    {
        "company": {
            "name": "garver",
            "id": "garver",
            "size": "1001-5000",
            "founded": "1919",
            "industry": "civil engineering",
            "website": "garverusa.com",
            "linkedin_url": "linkedin.com/company/garver",
            "location": {
                "locality": "north little rock",
                "region": "arkansas",
                "country": "united states",
                "continent": "north america",
                "geo": "34.76,-92.26",
                "street_address": "2049 e joyce blvd",
                "postal_code": "72703",
                "address_line_2": None,
            },
        },
        "start_date": "2019-10",
        "end_date": None,
        "is_primary": True,
        "summary": "Engineering firm.",
        "title": {
            "name": "recruiting manager",
            "role": "human_resources",
            "sub_role": "recruiting",
            "levels": ["manager"],
        },
    },
    {
        "company": {
            "name": "pointbank",
            "id": "point-bank",
            "size": "51-200",
            "founded": "1884",
            "industry": "banking",
            "location": {
                "locality": "pilot point",
                "region": "texas",
                "country": "united states",
            },
        },
        "start_date": "2014-01",
        "end_date": "2019-09",
        "is_primary": False,
        "summary": None,
        "title": {
            "name": "hr generalist",
            "role": "human_resources",
            "sub_role": "generalist",
            "levels": [],
        },
    },
]

PROFILES = [
    {
        "network": "linkedin",
        "id": "47878127",
        "url": "linkedin.com/in/joeyholland",
        "username": "joeyholland",
    },
]


def profile_row(**overrides):
    """A well-formed row, shaped like the real export."""
    row = {
        "linkedin_id": "47878127",
        "linkedin_username": "joeyholland",
        "linkedin_url": "linkedin.com/in/joeyholland",
        "first_name": "joseph",
        "last_name": "holland",
        "full_name": "joseph holland",
        "gender": "male",
        "industry": "civil engineering",
        "summary": "Recruiter.",
        "birth_year": "1985",
        "inferred_years_experience": "12",
        "linkedin_connections": "3761.0",
        "skills": repr(["recruiting", "leadership", "human resources"]),
        "interests": repr(["guitar", "aviation"]),
        "languages": repr([{"name": "english", "proficiency": None}]),
        "certifications": repr(
            [{"name": "certified scrum master (csm)", "organization": None,
              "start_date": "2017-07", "end_date": None}]
        ),
        "experience": repr(EXPERIENCE),
        "profiles": repr(PROFILES),
        "location_locality": "denton",
        "location_region": "texas",
        "location_country": "united states",
        "location_geo": "33.21,-97.13",
        "location_street_address": "3605 paint drive",
        "location_postal_code": "76210",
        "job_title": "recruiting manager",
        "job_title_role": "human_resources",
        "job_title_sub_role": "recruiting",
        "job_title_levels": repr(["manager"]),
        "job_company_id": "garver",
        "job_company_name": "garver",
        "job_start_date": "2019-10",
        "job_last_updated": "2020-12-01",
    }
    row.update(overrides)
    return row


def csv_document(rows, *, columns=None, extra_lines=()):
    """Render ``rows`` (dicts) as a CSV document, plus any raw trailing lines."""
    columns = columns or PROFILE_COLUMNS
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    for line in extra_lines:
        buffer.write(line + "\n")
    return buffer.getvalue()
