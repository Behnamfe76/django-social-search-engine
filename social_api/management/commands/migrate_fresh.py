"""Drop every table and run all migrations again -- ``migrate:fresh``."""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from social_api.services.database import drop_all_tables, list_tables


class Command(BaseCommand):
    help = "Drop every table in the database and re-run all migrations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Required to run against a database with DEBUG off.",
        )
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Drop the tables but leave the database empty.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "DEBUG is off -- refusing to drop tables without --force."
            )

        tables = list_tables()
        target = f"{connection.settings_dict['NAME']!r} on " \
                 f"{connection.settings_dict['HOST'] or 'localhost'}"

        if not tables:
            self.stdout.write(self.style.WARNING(f"No tables in {target}."))
        elif options["interactive"] and not self._confirm(len(tables), target):
            raise CommandError("Aborted.")

        dropped = drop_all_tables()
        self.stdout.write(
            self.style.SUCCESS(f"Dropped {len(dropped)} table(s) from {target}.")
        )

        if options["skip_migrate"]:
            return

        call_command("migrate", interactive=False, verbosity=options["verbosity"])
        self.stdout.write(self.style.SUCCESS("Migrations reapplied."))

    def _confirm(self, count, target):
        self.stdout.write(
            self.style.WARNING(
                f"This will permanently drop {count} table(s) from {target}."
            )
        )
        return input("Type 'yes' to continue: ").strip() == "yes"
