from rest_framework import serializers

from social_api.models import Personality


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
