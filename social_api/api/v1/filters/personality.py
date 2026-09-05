from django_filters import rest_framework as filters

from social_api.models import (
    Certification,
    Company,
    Industry,
    Interest,
    Language,
    OccupationLevel,
    OccupationRole,
    Personality,
    Skill,
)


def lookup_filter(field_name, queryset):
    """Filter profiles by one lookup dimension, by id.

    Repeatable, and ORed together: ``?skill_id=1&skill_id=2`` returns profiles
    with either skill, which is how a multi-select facet is expected to behave.
    Pass the same parameter twice for two values rather than a comma-separated
    list.

    ``distinct`` is on (django-filter's default here) because every one of these
    crosses a to-many relation -- without it a profile with three matching skills
    would come back three times.
    """
    return filters.ModelMultipleChoiceFilter(
        field_name=field_name,
        queryset=queryset,
    )


class PersonalityFilter(filters.FilterSet):
    full_name = filters.CharFilter(lookup_expr="icontains")
    birth_year_min = filters.NumberFilter(field_name="birth_year", lookup_expr="gte")
    birth_year_max = filters.NumberFilter(field_name="birth_year", lookup_expr="lte")

    # One filter per lookup endpoint, named so the id a profile carries can be
    # handed straight back: a chip from ``skills`` filters with ``?skill_id=``.
    industry_id = lookup_filter("industry", Industry.objects.all())
    skill_id = lookup_filter("skills", Skill.objects.all())
    interest_id = lookup_filter("interests", Interest.objects.all())
    language_id = lookup_filter("languages", Language.objects.all())
    certification_id = lookup_filter("certifications", Certification.objects.all())
    company_id = lookup_filter("employments__company", Company.objects.all())
    occupation_role_id = lookup_filter(
        "employments__occupation_role", OccupationRole.objects.all()
    )
    occupation_level_id = lookup_filter(
        "employments__level_links__occupation_level", OccupationLevel.objects.all()
    )

    class Meta:
        model = Personality
        fields = ["gender", "industry_id", "import_batch_id", "full_name"]
