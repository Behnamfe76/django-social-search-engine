"""Shared test helpers."""

from django.db import connection


def tables_exist(*names):
    """True when every named table is present in the current database.

    Company/Employment have no migration yet, so tests touching them skip instead
    of erroring on a missing relation.
    """
    with connection.cursor() as cursor:
        existing = set(connection.introspection.table_names(cursor))
    return set(names) <= existing
