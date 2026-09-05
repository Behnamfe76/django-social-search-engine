"""Operational database helpers.

Separate from the management command that calls them so the destructive part can
be exercised directly in a test, against a real connection, rather than only
through the CLI.
"""

from django.db import connection as default_connection


def list_tables(connection=None):
    """Every table in the connection's current schema, alphabetically."""
    connection = connection or default_connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = current_schema()
            ORDER BY tablename
            """
        )
        return [row[0] for row in cursor.fetchall()]


def drop_all_tables(connection=None):
    """Drop every table in the schema. Returns the names that were dropped.

    One statement with CASCADE, so foreign keys between the tables do not force
    an ordering and dependent views and sequences go with them. The schema itself
    is left in place -- dropping it would take any extensions with it, and this
    is meant to be the equivalent of "drop the tables", not "drop the database".
    """
    connection = connection or default_connection
    tables = list_tables(connection)
    if not tables:
        return []

    quoted = ", ".join(connection.ops.quote_name(table) for table in tables)
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {quoted} CASCADE")
    return tables
