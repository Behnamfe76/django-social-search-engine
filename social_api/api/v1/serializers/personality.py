from rest_framework import serializers

from social_api.models import Personality


class PersonalitySerializer(serializers.ModelSerializer):
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
        read_only_fields = ["id", "created_at", "updated_at"]
