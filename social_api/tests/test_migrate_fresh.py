from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from social_api.services.database import drop_all_tables, list_tables


class ListTablesTests(TestCase):
    def test_the_project_tables_are_visible(self):
        tables = list_tables()

        for expected in ("personalities", "companies", "import_batches", "import_chunks"):
            with self.subTest(table=expected):
                self.assertIn(expected, tables)


class DropAllTablesTests(TestCase):
    """Runs inside the test transaction, so the drop is rolled back afterwards.

    That is also the point: DDL here is transactional, which is what makes it
    safe to prove the behaviour rather than merely assert the SQL string.
    """

    def test_every_table_goes_including_djangos_own(self):
        self.assertNotEqual(list_tables(), [])

        dropped = drop_all_tables()

        self.assertEqual(list_tables(), [])
        self.assertIn("personalities", dropped)
        # django_migrations too, so migrate genuinely starts from zero.
        self.assertIn("django_migrations", dropped)

    def test_dropping_an_empty_schema_is_a_no_op(self):
        drop_all_tables()

        self.assertEqual(drop_all_tables(), [])


class MigrateFreshCommandTests(TestCase):
    """Django's test runner forces DEBUG off, so the development cases say so
    explicitly rather than relying on the ambient value."""

    @override_settings(DEBUG=False)
    def test_it_refuses_to_wipe_a_non_debug_database(self):
        with self.assertRaises(CommandError) as caught:
            call_command("migrate_fresh", "--noinput", stdout=StringIO())

        self.assertIn("--force", str(caught.exception))
        self.assertIn("personalities", list_tables())

    @override_settings(DEBUG=False)
    def test_force_overrides_the_guard(self):
        out = StringIO()

        call_command("migrate_fresh", "--noinput", "--force", "--skip-migrate", stdout=out)

        self.assertEqual(list_tables(), [])
        self.assertIn("Dropped", out.getvalue())

    @override_settings(DEBUG=True)
    def test_skip_migrate_leaves_the_database_empty(self):
        call_command("migrate_fresh", "--noinput", "--skip-migrate", stdout=StringIO())

        self.assertEqual(list_tables(), [])

    @override_settings(DEBUG=True)
    def test_without_skip_migrate_the_schema_comes_back(self):
        call_command("migrate_fresh", "--noinput", stdout=StringIO(), verbosity=0)

        tables = list_tables()
        self.assertIn("personalities", tables)
        self.assertIn("django_migrations", tables)
        self.assertIn("import_chunks", tables)
