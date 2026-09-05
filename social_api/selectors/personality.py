from django.db.models import Prefetch, QuerySet

from social_api.models import Employment, Personality

# Everything the serialized lookup collections read. Without these, rendering a
# page of 20 profiles costs a query per profile per dimension; with them the
# whole page is a fixed handful regardless of page size.
LOOKUP_PREFETCHES = (
    "skills",
    "interests",
    "languages",
    "certifications",
    Prefetch(
        "employments",
        queryset=Employment.objects.select_related(
            "company", "occupation_role"
        ).prefetch_related("level_links__occupation_level"),
    ),
)


def personality_queryset() -> QuerySet[Personality]:
    return Personality.objects.select_related("industry").filter(
        deleted_at__isnull=True
    )


def personality_with_lookups() -> QuerySet[Personality]:
    """The read queryset: the base plus everything the lookup fields render."""
    return personality_queryset().prefetch_related(*LOOKUP_PREFETCHES)
