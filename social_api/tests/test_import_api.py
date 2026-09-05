from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from social_api.models import ImportBatch, ImportRowError, Personality
from social_api.services.imports import dispatch
from social_api.tests.support import (
    TemporaryMediaMixin,
    authenticate,
    csv_document,
    profile_row,
)

IMPORTS_URL = "/api/v1/imports/"


def upload(name="profiles.csv", rows=None):
    document = csv_document(rows if rows is not None else [profile_row()])
    return SimpleUploadedFile(name, document.encode(), content_type="text/csv")


class ImportUploadTests(TemporaryMediaMixin, APITestCase):
    """The request stores the file and leaves; it never parses it."""

    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            email="importer@example.com", password="pw", name="Importer"
        )
        authenticate(self.client, self.user)

    def post(self, **kwargs):
        payload = {"file": upload(), "source": "people-data-labs"}
        payload.update(kwargs)
        return self.client.post(IMPORTS_URL, payload, format="multipart")

    def test_upload_is_accepted_without_being_processed(self):
        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], ImportBatch.Status.PENDING)
        self.assertIsNone(response.data["row_count"])
        # Nothing was read in-request: no rows, no plan.
        self.assertEqual(Personality.objects.count(), 0)
        self.assertEqual(ImportBatch.objects.get().total_chunks, 0)

    def test_response_points_at_the_resource_to_poll(self):
        response = self.post()

        batch_id = response.data["id"]
        self.assertTrue(
            response["Location"].endswith(f"{IMPORTS_URL}{batch_id}/"),
            response["Location"],
        )

    def test_the_batch_records_who_uploaded_what(self):
        self.post()

        batch = ImportBatch.objects.get()
        self.assertEqual(batch.user, self.user)
        self.assertEqual(batch.filename, "profiles.csv")
        self.assertEqual(batch.source, "people-data-labs")
        self.assertTrue(batch.file_size > 0)

    def test_planning_is_queued_only_after_the_row_commits(self):
        with mock.patch.object(dispatch, "plan_batch") as queued:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.post()
            queued.assert_called_once_with(response.data["id"])

    def test_an_empty_file_is_rejected(self):
        empty = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")

        response = self.post(file=empty)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ImportBatch.objects.exists())

    @override_settings(IMPORT_MAX_UPLOAD_BYTES=10)
    def test_an_oversized_file_is_rejected(self):
        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limit", str(response.data["file"]))

    def test_upload_requires_a_token(self):
        self.client.credentials()

        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ImportProgressTests(APITestCase):
    """The polling contract a client watches while workers run."""

    def setUp(self):
        super().setUp()
        authenticate(
            self.client,
            get_user_model().objects.create_user(
                email="watcher@example.com", password="pw", name="Watcher"
            ),
        )
        self.batch = ImportBatch.objects.create(
            source="people-data-labs",
            filename="profiles.csv",
            status=ImportBatch.Status.PROCESSING,
            row_count=100,
            total_chunks=4,
            pending_chunks=3,
            processed_rows=25,
            created_rows=20,
            updated_rows=3,
            failed_rows=2,
        )

    def detail(self):
        return self.client.get(f"{IMPORTS_URL}{self.batch.pk}/")

    def test_progress_is_derived_from_the_worker_counters(self):
        body = self.detail().data

        self.assertEqual(body["progress"], 25.0)
        self.assertEqual(body["processed_rows"], 25)
        self.assertEqual(body["pending_chunks"], 3)
        self.assertEqual(body["total_chunks"], 4)
        self.assertFalse(body["is_terminal"])

    def test_a_finished_batch_reports_terminal(self):
        ImportBatch.objects.filter(pk=self.batch.pk).update(
            status=ImportBatch.Status.PARTIAL, pending_chunks=0, processed_rows=100
        )

        body = self.detail().data

        self.assertTrue(body["is_terminal"])
        self.assertEqual(body["progress"], 100.0)

    def test_a_batch_that_has_not_been_planned_reports_zero(self):
        ImportBatch.objects.filter(pk=self.batch.pk).update(
            status=ImportBatch.Status.PENDING, row_count=None, processed_rows=0
        )

        self.assertEqual(self.detail().data["progress"], 0.0)

    def test_progress_requires_a_token(self):
        self.client.credentials()

        self.assertEqual(self.detail().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejected_rows_are_listed_separately(self):
        ImportRowError.objects.create(
            batch=self.batch, row_number=7, message="expected 32 columns, got 3", excerpt="1,2,3"
        )

        body = self.client.get(f"{IMPORTS_URL}{self.batch.pk}/errors/").data

        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["row_number"], 7)
        self.assertEqual(body["results"][0]["excerpt"], "1,2,3")

    def test_batches_are_listed_newest_first(self):
        later = ImportBatch.objects.create(source="test", filename="later.csv")

        body = self.client.get(IMPORTS_URL).data

        self.assertEqual([row["id"] for row in body["results"]], [later.pk, self.batch.pk])
