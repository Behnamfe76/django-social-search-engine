from django_filters import rest_framework as filters

from social_api.models import Personality


class PersonalityFilter(filters.FilterSet):
    full_name = filters.CharFilter(lookup_expr="icontains")
    birth_year_min = filters.NumberFilter(field_name="birth_year", lookup_expr="gte")
    birth_year_max = filters.NumberFilter(field_name="birth_year", lookup_expr="lte")

    class Meta:
        model = Personality
        fields = ["gender", "industry_id", "import_batch_id", "full_name"]
