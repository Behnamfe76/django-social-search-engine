from django.conf import settings
from rest_framework import serializers

from social_api.models import ImportBatch, ImportRowError


class ImportBatchCreateSerializer(serializers.ModelSerializer):
    """Accepts the upload itself; everything else is derived from it."""

    file = serializers.FileField(write_only=True)
    source = serializers.CharField(
        required=False, default="people-data-labs", max_length=255
    )

    class Meta:
        model = ImportBatch
        fields = ["id", "source", "file"]
        read_only_fields = ["id"]

    def validate_file(self, value):
        limit = settings.IMPORT_MAX_UPLOAD_BYTES
        if value.size > limit:
            raise serializers.ValidationError(
                f"File is {value.size} bytes, over the {limit} byte limit."
            )
        if not value.size:
            raise serializers.ValidationError("File is empty.")
        return value

    def create(self, validated_data):
        upload = validated_data.pop("file")
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return ImportBatch.objects.create(
            user=user if user is not None and user.is_authenticated else None,
            source=validated_data.get("source") or "people-data-labs",
            filename=upload.name[:255],
            file=upload,
            file_size=upload.size,
        )


class ImportBatchStatusSerializer(serializers.ModelSerializer):
    """The shape the progress poller reads."""

    progress = serializers.FloatField(read_only=True)
    duration_seconds = serializers.FloatField(read_only=True, allow_null=True)
    is_terminal = serializers.BooleanField(read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "status",
            "source",
            "filename",
            "file_size",
            "row_count",
            "total_chunks",
            "pending_chunks",
            "processed_rows",
            "created_rows",
            "updated_rows",
            "failed_rows",
            "progress",
            "duration_seconds",
            "is_terminal",
            "error",
            "started_at",
            "finished_at",
            "created_at",
        ]
        read_only_fields = fields


class ImportRowErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRowError
        fields = ["id", "row_number", "message", "excerpt", "created_at"]
        read_only_fields = fields
