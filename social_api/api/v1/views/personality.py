from django.utils import timezone
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from social_api.api.v1.serializers import (
    PersonalityCreateSerializer,
    PersonalityListSerializer,
    PersonalityRetrieveSerializer,
    PersonalityUpdateSerializer,
)
from social_api.selectors.personality import personality_queryset


class PersonalityPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PersonalityViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalityRetrieveSerializer
    pagination_class = PersonalityPagination
    filterset_fields = ["gender", "industry_id", "import_batch_id"]
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
