from rest_framework import serializers

from social_api.models import Industry, Personality


def industry_id_field():
    """Keep ``industry_id`` writable in the payload now that ``industry`` is a FK.

    Without this DRF builds a ReadOnlyField for the ``_id`` attname and silently
    drops the value on write.
    """
    return serializers.PrimaryKeyRelatedField(
        source="industry",
        queryset=Industry.objects.all(),
        required=False,
        allow_null=True,
    )


class PersonalityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personality
        fields = [
            "id",
            "industry_id",
            "full_name",
            "gender",
            "created_at",
        ]
        read_only_fields = fields


class PersonalityRetrieveSerializer(serializers.ModelSerializer):
    industry_id = industry_id_field()

    class Meta:
        model = Personality
        fields = [
            "id",
            "import_batch_id",
            "industry_id",
            "first_name",
            "middle_name",
            "middle_initial",
            "last_name",
            "full_name",
            "gender",
            "birth_date",
            "birth_year",
            "summary",
            "inferred_salary",
            "inferred_years_experience",
            "version_status",
            "location_last_updated",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["id", "full_name", "created_at", "updated_at", "deleted_at"]


class PersonalityCreateSerializer(serializers.ModelSerializer):
    industry_id = industry_id_field()

    class Meta:
        model = Personality
        fields = [
            "id",
            "import_batch_id",
            "industry_id",
            "first_name",
            "middle_name",
            "middle_initial",
            "last_name",
            "full_name",
            "gender",
            "birth_date",
            "birth_year",
            "summary",
            "inferred_salary",
            "inferred_years_experience",
            "version_status",
            "location_last_updated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "created_at", "updated_at"]


class PersonalityUpdateSerializer(serializers.ModelSerializer):
    industry_id = industry_id_field()

    class Meta:
        model = Personality
        fields = [
            "id",
            "import_batch_id",
            "industry_id",
            "first_name",
            "middle_name",
            "middle_initial",
            "last_name",
            "full_name",
            "gender",
            "birth_date",
            "birth_year",
            "summary",
            "inferred_salary",
            "inferred_years_experience",
            "version_status",
            "location_last_updated",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "updated_at"]
