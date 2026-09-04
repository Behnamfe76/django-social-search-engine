from django.utils import timezone
from rest_framework import viewsets

from social_api.api.v1.filters import PersonalityFilter
from social_api.api.v1.serializers import (
    PersonalityCreateSerializer,
    PersonalityListSerializer,
    PersonalityRetrieveSerializer,
    PersonalityUpdateSerializer,
)
from social_api.selectors.personality import personality_queryset


class PersonalityViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalityRetrieveSerializer
    filterset_class = PersonalityFilter
    search_fields = ["full_name", "first_name", "last_name"]
    ordering_fields = ["id", "full_name", "last_name", "created_at", "updated_at"]
    ordering = ["id"]
    serializer_action_classes = {
        "list": PersonalityListSerializer,
        "retrieve": PersonalityRetrieveSerializer,
        "create": PersonalityCreateSerializer,
        "update": PersonalityUpdateSerializer,
        "partial_update": PersonalityUpdateSerializer,
    }

    def get_queryset(self):
        return personality_queryset()

    def get_serializer_class(self):
        return self.serializer_action_classes.get(self.action, self.serializer_class)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
