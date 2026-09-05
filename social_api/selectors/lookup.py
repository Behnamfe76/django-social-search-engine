"""Reference lists that back the front end's filter widgets.

Every lookup answers the same question -- "what may I filter by, and how many
profiles would each option match?" -- so they share one queryset shape:
``id``, ``name``, ``count``, ordered by name.

Two details are load-bearing:

``name`` is aliased in for the models whose label column is ``title``, so all
eight endpoints return an identical row and the front end needs one component
rather than one per dimension.

The count excludes soft-deleted profiles, matching ``personality_queryset``. A
filter option advertising 12 matches must not return 9 rows when clicked.
"""

from django.db.models import Count, F, Q

from social_api.models import (
    Certification,
    Company,
    Industry,
    Interest,
    Language,
    OccupationLevel,
    OccupationRole,
    Skill,
)

# Path from each lookup model to the profiles behind it. It must terminate at
# ``Personality`` so the soft-delete filter below can be appended to it, and it
# must reach a concrete column: the attribute join tables use composite primary
# keys, which Postgres cannot COUNT(DISTINCT).
COUNT_PATHS = {
    Industry: "personalities",
    Skill: "personality_links__personality",
    Interest: "personality_links__personality",
    Language: "personality_links__personality",
    Certification: "personality_links__personality",
    Company: "employments__personality",
    OccupationRole: "employments__personality",
    OccupationLevel: "employment_links__employment__personality",
}

# Models whose label lives in ``title`` rather than ``name``.
TITLE_LABELLED = {OccupationRole, OccupationLevel}


def lookup_queryset(model):
    """``id`` and a live profile count, ordered for a picker.

    Ordering is ``(pk)`` rather than ``name`` alone. Cursor pagination
    positions itself on the first ordering field and walks ties with an offset,
    which is only stable if the rest of the ordering is deterministic -- and
    none of these tables constrain ``name`` to be unique.
    """
    queryset = model.objects.all()

    if model in TITLE_LABELLED:
        queryset = queryset.annotate(name=F("title"))

    path = COUNT_PATHS[model]
    return queryset.annotate(
        count=Count(
            path,
            distinct=True,
            filter=Q(**{f"{path}__deleted_at__isnull": True}),
        )
    ).order_by("pk")
