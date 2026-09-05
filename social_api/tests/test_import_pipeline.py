from unittest import mock

from django.core.files.base import ContentFile
from django.db import OperationalError
from django.test import TransactionTestCase, override_settings

from social_api.models import (
    Certification,
    Company,
    Employment,
    ImportBatch,
    ImportChunk,
    ImportRowError,
    Location,
    Personality,
    PersonalityLocation,
    Skill,
    SocialProfiles,
)
from social_api.services.imports import dispatch, pipeline
from social_api.services.imports.row_importer import ChunkImporter
from social_api.tests.support import (
    EagerCeleryMixin,
    TemporaryMediaMixin,
    csv_document,
    profile_row,
)

# One row per chunk, so every test exercises the fan-out and the counter fan-in
# rather than the single-chunk shortcut.
ONE_ROW_PER_CHUNK = override_settings(IMPORT_CHUNK_MAX_ROWS=1)


class ImportPipelineTestCase(EagerCeleryMixin, TemporaryMediaMixin, TransactionTestCase):
    """Drives the real tasks inline, so on_commit hand-offs actually fire."""

    def run_import(self, document, **kwargs):
        payload = document.encode()
        batch = ImportBatch.objects.create(
            source="test",
            filename="profiles.csv",
            file=ContentFile(payload, name="profiles.csv"),
            file_size=len(payload),
            **kwargs,
        )
        pipeline.plan_batch(batch.pk)
        batch.refresh_from_db()
        return batch


@ONE_ROW_PER_CHUNK
class ImportPipelineTests(ImportPipelineTestCase):
    def test_a_profile_and_everything_hanging_off_it_is_imported(self):
        batch = self.run_import(csv_document([profile_row()]))

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        person = Personality.objects.get(external_id="47878127")
        self.assertEqual(person.full_name, "joseph holland")
        self.assertEqual(person.gender, "male")
        self.assertEqual(person.industry.name, "civil engineering")
        self.assertEqual(person.skills.count(), 3)
        self.assertEqual(person.interests.count(), 2)
        self.assertEqual(person.languages.count(), 1)
        self.assertEqual(person.certifications.count(), 1)

    def test_employment_history_comes_from_the_nested_experience_cell(self):
        self.run_import(csv_document([profile_row()]))

        person = Personality.objects.get(external_id="47878127")
        self.assertEqual(person.employments.count(), 2)

        current = person.employments.get(is_current=True)
        self.assertEqual(current.title, "recruiting manager")
        self.assertEqual(current.company.name, "garver")
        self.assertEqual(current.occupation_role.title, "human_resources")
        self.assertEqual(current.occupation_sub_role.title, "recruiting")
        self.assertEqual(
            [link.occupation_level.title for link in current.level_links.all()],
            ["manager"],
        )

    def test_companies_and_locations_are_resolved_once_and_shared(self):
        self.run_import(csv_document([profile_row()]))

        company = Company.objects.get(external_id="garver")
        self.assertEqual(company.founded_year, 1919)
        self.assertEqual(company.website, "https://garverusa.com")
        self.assertEqual(company.location.locality, "north little rock")

        home = Location.objects.get(locality="denton")
        self.assertEqual(home.name, Location.LocationName.CITY)
        self.assertEqual(str(home.latitude), "33.210000")
        link = PersonalityLocation.objects.get(location=home)
        self.assertTrue(link.is_primary)
        self.assertEqual(link.street_address, "3605 paint drive")

    def test_social_profiles_carry_the_connection_count(self):
        self.run_import(csv_document([profile_row()]))

        profile = SocialProfiles.objects.get(social_platform__slug="linkedin")
        self.assertEqual(profile.user_name, "joeyholland")
        self.assertEqual(profile.connection_count, 3761)

    def test_the_upload_is_deleted_once_the_batch_finishes(self):
        batch = self.run_import(csv_document([profile_row()]))

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertFalse(batch.file)

    @override_settings(IMPORT_DELETE_FILE_WHEN_DONE=False)
    def test_the_upload_can_be_kept_for_debugging(self):
        batch = self.run_import(csv_document([profile_row()]))

        self.assertTrue(batch.file)

    def test_counters_add_up_across_chunks(self):
        rows = [
            profile_row(linkedin_id=str(index), linkedin_username=f"user{index}")
            for index in range(5)
        ]
        batch = self.run_import(csv_document(rows))

        self.assertEqual(batch.total_chunks, 5)
        self.assertEqual(batch.pending_chunks, 0)
        self.assertEqual(batch.row_count, 5)
        self.assertEqual(batch.processed_rows, 5)
        self.assertEqual(batch.created_rows, 5)
        self.assertEqual(batch.failed_rows, 0)
        self.assertEqual(batch.progress, 100.0)
        self.assertEqual(Personality.objects.count(), 5)

    def test_reimporting_updates_instead_of_duplicating(self):
        document = csv_document([profile_row()])
        self.run_import(document)
        second = self.run_import(document)

        self.assertEqual(Personality.objects.count(), 1)
        self.assertEqual(second.created_rows, 0)
        self.assertEqual(second.updated_rows, 1)
        # The joins are re-inserted with ignore_conflicts, not stacked.
        self.assertEqual(Personality.objects.get().skills.count(), 3)
        self.assertEqual(Employment.objects.count(), 2)
        self.assertEqual(Skill.objects.count(), 3)
        self.assertEqual(Certification.objects.count(), 1)

    def test_a_repeated_identity_inside_one_file_collapses_to_one_profile(self):
        rows = [profile_row(), profile_row(last_name="hollande", full_name="joseph hollande")]
        batch = self.run_import(csv_document(rows))

        self.assertEqual(Personality.objects.count(), 1)
        self.assertEqual(Personality.objects.get().last_name, "hollande")
        self.assertEqual((batch.created_rows, batch.updated_rows), (1, 1))

    def test_a_row_without_an_identity_is_inserted_unconditionally(self):
        row = profile_row(linkedin_id="", linkedin_username="", linkedin_url="")
        batch = self.run_import(csv_document([row, row]))

        self.assertEqual(Personality.objects.count(), 2)
        self.assertIsNone(Personality.objects.first().external_id)
        self.assertEqual(batch.created_rows, 2)


@ONE_ROW_PER_CHUNK
class ImportFailureTests(ImportPipelineTestCase):
    def test_ragged_rows_are_recorded_and_the_batch_ends_partial(self):
        document = csv_document([profile_row()], extra_lines=["1,2,3"])
        batch = self.run_import(document)

        self.assertEqual(batch.status, ImportBatch.Status.PARTIAL)
        self.assertEqual(batch.created_rows, 1)
        self.assertEqual(batch.failed_rows, 1)
        self.assertEqual(batch.processed_rows, 2)

        error = ImportRowError.objects.get()
        self.assertEqual(error.row_number, 2)
        self.assertIn("expected 32 columns, got 3", error.message)
        self.assertEqual(error.excerpt, "1,2,3")

    def test_a_nameless_row_fails_alone_and_leaves_its_neighbours_alone(self):
        rows = [
            profile_row(),
            profile_row(
                linkedin_id="99", first_name="", last_name="", full_name=""
            ),
        ]
        batch = self.run_import(csv_document(rows))

        self.assertEqual(batch.status, ImportBatch.Status.PARTIAL)
        self.assertEqual(batch.created_rows, 1)
        self.assertEqual(batch.failed_rows, 1)
        self.assertIn("no usable name", ImportRowError.objects.get().message)
        self.assertEqual(Personality.objects.count(), 1)

    def test_an_empty_file_finishes_instead_of_hanging(self):
        batch = self.run_import("linkedin_id,first_name\n")

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(batch.total_chunks, 0)
        self.assertEqual(batch.row_count, 0)

    def test_a_batch_with_no_file_is_failed_not_crashed(self):
        batch = ImportBatch.objects.create(source="test", filename="missing.csv")

        pipeline.plan_batch(batch.pk)

        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertIn("no stored file", batch.error)


@ONE_ROW_PER_CHUNK
class ImportIdempotencyTests(ImportPipelineTestCase):
    """At-least-once delivery means every task must survive a second run."""

    def test_a_redelivered_chunk_is_ignored(self):
        batch = self.run_import(csv_document([profile_row()]))
        chunk = ImportChunk.objects.get()

        pipeline.process_chunk(chunk.pk)

        batch.refresh_from_db()
        self.assertEqual(batch.processed_rows, 1)
        self.assertEqual(batch.created_rows, 1)
        self.assertEqual(batch.pending_chunks, 0)

    def test_a_redelivered_plan_is_ignored(self):
        batch = self.run_import(csv_document([profile_row()]))

        pipeline.plan_batch(batch.pk)

        batch.refresh_from_db()
        self.assertEqual(batch.total_chunks, 1)
        self.assertEqual(ImportChunk.objects.count(), 1)
        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)

    def test_finalising_twice_does_not_reopen_the_batch(self):
        batch = self.run_import(csv_document([profile_row()]))
        finished_at = batch.finished_at

        pipeline.finalise_batch(batch.pk)

        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(batch.finished_at, finished_at)

    def test_a_chunk_whose_retries_run_out_cannot_stall_the_batch(self):
        rows = [profile_row(linkedin_id="1"), profile_row(linkedin_id="2")]
        # Hold the chunks back so one can be abandoned the way an exhausted task
        # would abandon it.
        with mock.patch.object(dispatch, "process_chunk"):
            batch = self.run_import(csv_document(rows))
        self.assertEqual(batch.status, ImportBatch.Status.PROCESSING)

        first, second = ImportChunk.objects.order_by("index")
        pipeline.process_chunk(first.pk)
        pipeline.abandon_chunk(second.pk, RuntimeError("worker lost"))

        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportBatch.Status.PARTIAL)
        self.assertEqual(batch.pending_chunks, 0)
        self.assertEqual(batch.created_rows, 1)
        self.assertEqual(batch.failed_rows, 1)
        self.assertIn("abandoned", ImportRowError.objects.get().message)


@ONE_ROW_PER_CHUNK
class DeadlockRetryTests(ImportPipelineTestCase):
    """Concurrent chunks upsert the same companies and lookup rows constantly."""

    @staticmethod
    def deadlock():
        cause = Exception("deadlock detected")
        cause.sqlstate = "40P01"
        error = OperationalError("deadlock detected")
        error.__cause__ = cause
        return error

    def test_a_row_that_loses_a_deadlock_is_retried_not_dropped(self):
        with mock.patch.object(
            ChunkImporter, "import_row", side_effect=[self.deadlock(), True]
        ) as attempt:
            batch = self.run_import(csv_document([profile_row()]))

        self.assertEqual(attempt.call_count, 2)
        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(batch.created_rows, 1)
        self.assertEqual(batch.failed_rows, 0)

    def test_a_row_that_keeps_losing_is_eventually_recorded(self):
        with mock.patch.object(
            ChunkImporter, "import_row", side_effect=self.deadlock
        ):
            batch = self.run_import(csv_document([profile_row()]))

        self.assertEqual(batch.status, ImportBatch.Status.PARTIAL)
        self.assertEqual(batch.failed_rows, 1)
        self.assertIn("deadlock", ImportRowError.objects.get().message)

    def test_an_error_postgres_does_not_want_retried_fails_immediately(self):
        error = OperationalError("connection gone")
        with mock.patch.object(
            ChunkImporter, "import_row", side_effect=error
        ) as attempt:
            batch = self.run_import(csv_document([profile_row()]))

        self.assertEqual(attempt.call_count, 1)
        self.assertEqual(batch.failed_rows, 1)
