from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.reverse import reverse

from django.db import transaction

from social_api.api.v1.serializers import (
    ImportBatchCreateSerializer,
    ImportBatchStatusSerializer,
    ImportRowErrorSerializer,
)
from social_api.selectors.import_batch import (
    import_batch_queryset,
    import_row_error_queryset,
)
from social_api.services.imports import dispatch


@extend_schema_view(
    list=extend_schema(tags=["imports"], summary="List import batches"),
    retrieve=extend_schema(
        tags=["imports"],
        summary="Import progress",
        description=(
            "Poll this while a batch runs. Counters are updated by the workers as "
            "each chunk commits, so progress advances without the request ever "
            "touching the file."
        ),
    ),
)
class ImportBatchViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Upload a dataset and watch the workers chew through it."""

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ImportBatchStatusSerializer
    serializer_action_classes = {"create": ImportBatchCreateSerializer}

    def get_queryset(self):
        return import_batch_queryset()

    def get_serializer_class(self):
        return self.serializer_action_classes.get(self.action, self.serializer_class)

    @extend_schema(
        tags=["imports"],
        summary="Start an import",
        description=(
            "Stores the upload and returns immediately with 202. Planning and "
            "importing happen on the queue; poll the returned resource for progress."
        ),
        request={"multipart/form-data": ImportBatchCreateSerializer},
        responses={202: ImportBatchStatusSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()

        # Queued only once the row is durably committed, so a worker can never
        # pick up a batch the web process has not finished writing.
        transaction.on_commit(lambda: dispatch.plan_batch(batch.pk))

        body = ImportBatchStatusSerializer(batch, context=self.get_serializer_context())
        location = reverse(
            "social_api:v1:import-detail", kwargs={"pk": batch.pk}, request=request
        )
        return Response(
            body.data, status=status.HTTP_202_ACCEPTED, headers={"Location": location}
        )

    @extend_schema(
        tags=["imports"],
        summary="Rows the importer rejected",
        responses={200: ImportRowErrorSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="errors")
    def errors(self, request, pk=None):
        queryset = import_row_error_queryset(self.get_object())
        page = self.paginate_queryset(queryset)
        serializer = ImportRowErrorSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
