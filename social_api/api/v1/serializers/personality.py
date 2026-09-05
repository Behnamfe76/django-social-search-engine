from rest_framework import serializers

from social_api.models import ImportBatch, Industry, Personality


def fk_id_field(source, queryset):
    """Expose a FK as its ``<name>_id`` while keeping it writable.

    Without an explicit declaration DRF builds a ReadOnlyField for the ``_id``
    attname of a relation and silently drops the value on write.
    """
    return serializers.PrimaryKeyRelatedField(
        source=source,
        queryset=queryset,
        required=False,
        allow_null=True,
    )


def industry_id_field():
    return fk_id_field("industry", Industry.objects.all())


def import_batch_id_field():
    return fk_id_field("import_batch", ImportBatch.objects.all())


class PersonalityListSerializer(serializers.ModelSerializer):
    industry = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Personality
        fields = [
            "id",
            "industry",
            "full_name",
            "gender",
            "created_at",
        ]
        read_only_fields = ["id", "full_name", "gender", "created_at"]


class PersonalityRetrieveSerializer(serializers.ModelSerializer):
    industry_id = industry_id_field()
    import_batch_id = import_batch_id_field()

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
    import_batch_id = import_batch_id_field()

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
    import_batch_id = import_batch_id_field()

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
