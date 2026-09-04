from django.utils import timezone
from rest_framework import viewsets

from social_api.api.v1.serializers import PersonalitySerializer
from social_api.selectors.personality import personality_queryset


class PersonalityViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalitySerializer
    filterset_fields = ["gender", "industry_id", "import_batch_id"]
    search_fields = ["full_name", "first_name", "last_name"]
    ordering_fields = ["id", "full_name", "last_name", "created_at", "updated_at"]
    ordering = ["id"]

    def get_queryset(self):
        return personality_queryset()

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
