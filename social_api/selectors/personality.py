from django.db.models import QuerySet

from social_api.models import Personality


def personality_queryset() -> QuerySet[Personality]:
    return Personality.objects.filter(deleted_at__isnull=True)
