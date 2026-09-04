import unittest

from rest_framework import status
from rest_framework.test import APITestCase

from social_api.models import ImportBatch, Industry, Personality
from social_api.tests.support import tables_exist


@unittest.skipUnless(tables_exist("industries"), "industries table has no migration yet")
class PersonalityIndustryFieldTests(APITestCase):
    """``industry`` is a FK but the API exposes it as ``industry_id``.

    DRF builds a ReadOnlyField for an ``_id`` attname unless the field is declared
    explicitly, which silently drops the value on write - hence these tests.
    """

    def setUp(self):
        self.software = Industry.objects.create(name="Software", slug="software")
        self.finance = Industry.objects.create(name="Finance", slug="finance")

    def test_create_persists_industry_id(self):
        response = self.client.post(
            "/api/v1/personalities/",
            {"first_name": "Grace", "last_name": "Hopper", "industry_id": self.finance.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["industry_id"], self.finance.pk)
        self.assertEqual(Personality.objects.get(first_name="Grace").industry, self.finance)

    def test_industry_id_is_optional(self):
        response = self.client.post(
            "/api/v1/personalities/",
            {"first_name": "No", "last_name": "Industry"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(Personality.objects.get(first_name="No").industry)

    def test_patch_updates_industry_id(self):
        person = Personality.objects.create(
            first_name="Ada", last_name="Lovelace", industry=self.finance
        )

        response = self.client.patch(
            f"/api/v1/personalities/{person.pk}/",
            {"industry_id": self.software.pk},
            format="json",
        )
        person.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(person.industry, self.software)

    def test_unknown_industry_id_is_rejected(self):
        response = self.client.post(
            "/api/v1/personalities/",
            {"first_name": "Bad", "last_name": "Ref", "industry_id": 9999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("industry_id", response.data)

    def test_list_filters_by_industry_id(self):
        Personality.objects.create(first_name="Ada", last_name="Lovelace", industry=self.software)
        Personality.objects.create(first_name="Alan", last_name="Turing", industry=self.finance)

        response = self.client.get(f"/api/v1/personalities/?industry_id={self.software.pk}")

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["full_name"], "Ada Lovelace")


@unittest.skipUnless(tables_exist("import_batches", "users"), "app tables have no migration yet")
class PersonalityImportBatchFieldTests(APITestCase):
    """Same ``_id``-on-a-FK trap as industry_id; see PersonalityIndustryFieldTests."""

    def setUp(self):
        self.batch = ImportBatch.objects.create(
            source="people-data-labs", filename="batch1.json", row_count=10
        )

    def test_create_persists_import_batch_id(self):
        response = self.client.post(
            "/api/v1/personalities/",
            {"first_name": "Grace", "last_name": "Hopper", "import_batch_id": self.batch.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["import_batch_id"], self.batch.pk)
        self.assertEqual(Personality.objects.get(first_name="Grace").import_batch, self.batch)

    def test_unknown_import_batch_id_is_rejected(self):
        response = self.client.post(
            "/api/v1/personalities/",
            {"first_name": "Bad", "last_name": "Ref", "import_batch_id": 9999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("import_batch_id", response.data)

    def test_list_filters_by_import_batch_id(self):
        Personality.objects.create(first_name="Ada", last_name="Lovelace", import_batch=self.batch)
        Personality.objects.create(first_name="Alan", last_name="Turing")

        response = self.client.get(f"/api/v1/personalities/?import_batch_id={self.batch.pk}")

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["full_name"], "Ada Lovelace")
