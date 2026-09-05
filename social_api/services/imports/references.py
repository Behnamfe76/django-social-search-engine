"""Bulk get-or-create for the shared lookup tables.

``get_or_create`` costs a query per distinct label, and a single chunk of profiles
carries hundreds of distinct skills while sibling workers insert the same
vocabulary concurrently. Instead each table is warmed once per chunk: every unseen
label is inserted in one ``bulk_create(ignore_conflicts=True)`` -- letting the
unique slug constraint absorb the races rather than trying to avoid them -- and
then read back in a single query. Cost stays flat as chunks grow.

Slug is the unique column on these tables, so it is also the cache key. Two labels
that slugify identically therefore share a row, which is a property of the schema
rather than of this cache.
"""

from social_api.models import (
    Certification,
    Industry,
    Interest,
    Language,
    Occupation,
    OccupationLevel,
    OccupationRole,
    Skill,
)
from social_api.services.slug import build_slug

LABEL_MAX_LENGTH = 255


class LabelTable:
    """One lookup table, cached and resolved in bulk."""

    def __init__(self, model, *, label_field="name"):
        self.model = model
        self.label_field = label_field
        self._rows = {}

    def warm(self, labels, extras=None):
        """Ensure every label in ``labels`` exists and is cached."""
        pending = {}
        for label in labels:
            slug = self._slug(label)
            if slug and slug not in self._rows and slug not in pending:
                pending[slug] = label
        if not pending:
            return

        # Sorted, so every worker inserting the same vocabulary takes its locks
        # in the same order and concurrent chunks cannot deadlock on each other.
        self.model.objects.bulk_create(
            [
                self.model(
                    slug=slug,
                    **{self.label_field: pending[slug][:LABEL_MAX_LENGTH]},
                    **((extras or {}).get(pending[slug]) or {}),
                )
                for slug in sorted(pending)
            ],
            ignore_conflicts=True,
        )
        for row in self.model.objects.filter(slug__in=list(pending)):
            self._rows[row.slug] = row

    def get(self, label):
        """Return the row for ``label``, warming the cache if it is a first sighting."""
        slug = self._slug(label)
        if not slug:
            return None
        if slug not in self._rows:
            self.warm([label])
        return self._rows.get(slug)

    def get_many(self, labels):
        resolved = []
        seen = set()
        for label in labels:
            row = self.get(label)
            if row is not None and row.pk not in seen:
                seen.add(row.pk)
                resolved.append(row)
        return resolved

    def _slug(self, label):
        if not label:
            return None
        try:
            return build_slug(label, max_length=LABEL_MAX_LENGTH)
        except ValueError:
            # Nothing sluggable, e.g. a skill recorded as "++". Not importable.
            return None


class References:
    """The set of lookup tables one chunk needs, warmed together."""

    def __init__(self):
        self.industries = LabelTable(Industry)
        self.skills = LabelTable(Skill)
        self.interests = LabelTable(Interest)
        self.languages = LabelTable(Language)
        self.certifications = LabelTable(Certification)
        self.occupations = LabelTable(Occupation, label_field="title")
        self.occupation_roles = LabelTable(OccupationRole, label_field="title")
        self.occupation_levels = LabelTable(OccupationLevel, label_field="title")
