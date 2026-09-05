from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from social_api.api.v1.serializers.lookup import LookupRefSerializer, TitleRefSerializer
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


class LookupFieldsMixin(serializers.Serializer):
    """The lookup dimensions a profile belongs to, embedded as ``{id, name}``.

    Every list here matches a filter on ``PersonalityFilter``, so a value read
    off a profile can be handed straight back as ``?<name>_id=``.

    The last three are not relations on ``Personality`` -- they hang off its
    employments -- so they are derived and de-duplicated here. They read from
    prefetched rows (see ``personality_queryset``); without that prefetch each
    profile in a list page would cost its own queries.
    """

    skills = LookupRefSerializer(many=True, read_only=True)
    interests = LookupRefSerializer(many=True, read_only=True)
    languages = LookupRefSerializer(many=True, read_only=True)
    certifications = LookupRefSerializer(many=True, read_only=True)
    companies = serializers.SerializerMethodField()
    occupation_roles = serializers.SerializerMethodField()
    occupation_levels = serializers.SerializerMethodField()

    LOOKUP_FIELDS = [
        "skills",
        "interests",
        "languages",
        "certifications",
        "companies",
        "occupation_roles",
        "occupation_levels",
    ]

    def _unique(self, items, serializer):
        """Serialize in first-seen order, one row per id."""
        seen = {}
        for item in items:
            if item is not None and item.pk not in seen:
                seen[item.pk] = item
        return serializer(seen.values(), many=True).data

    @extend_schema_field(LookupRefSerializer(many=True))
    def get_companies(self, personality):
        return self._unique(
            [employment.company for employment in personality.employments.all()],
            LookupRefSerializer,
        )

    @extend_schema_field(TitleRefSerializer(many=True))
    def get_occupation_roles(self, personality):
        return self._unique(
            [employment.occupation_role for employment in personality.employments.all()],
            TitleRefSerializer,
        )

    @extend_schema_field(TitleRefSerializer(many=True))
    def get_occupation_levels(self, personality):
        return self._unique(
            [
                link.occupation_level
                for employment in personality.employments.all()
                for link in employment.level_links.all()
            ],
            TitleRefSerializer,
        )


class PersonalityListSerializer(LookupFieldsMixin, serializers.ModelSerializer):
    industry = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Personality
        fields = [
            "id",
            "industry",
            "full_name",
            "gender",
            "created_at",
            *LookupFieldsMixin.LOOKUP_FIELDS,
        ]
        # ``industry`` and the lookup collections are declared above and already
        # read-only; DRF forbids naming a declared field here.
        read_only_fields = ["id", "full_name", "gender", "created_at"]


class PersonalityRetrieveSerializer(LookupFieldsMixin, serializers.ModelSerializer):
    industry_id = industry_id_field()
    import_batch_id = import_batch_id_field()
    # The label next to the writable id, so a detail view needs no second call.
    industry = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Personality
        fields = [
            "id",
            "import_batch_id",
            "industry_id",
            "industry",
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
            *LookupFieldsMixin.LOOKUP_FIELDS,
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
