"""Read-only reference lists for the front end's filter widgets.

Each viewset is the same endpoint over a different dimension, so the behaviour
lives on the base class and the subclasses carry only a model and a tag.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets

from social_api.api.v1.pagination import LookupCursorPagination
from social_api.api.v1.serializers import LookupSerializer
from social_api.models import (
    Certification,
    Company,
    Industry,
    Interest,
    Language,
    OccupationLevel,
    OccupationRole,
    Skill,
)
from social_api.selectors.lookup import lookup_queryset


class LookupViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve one dimension's filter options.

    ``filter_backends`` is narrowed to search on purpose. The project default
    includes ``OrderingFilter``, and ``CursorPagination.get_ordering`` defers to
    an ordering backend when one is present -- a client-supplied ``?ordering=``
    would then change the sort out from under an already-issued cursor. Search
    stays, because a picker over 1400 skills is unusable without type-ahead.
    """

    serializer_class = LookupSerializer
    pagination_class = LookupCursorPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
    model = None

    def get_queryset(self):
        return lookup_queryset(self.model)


def lookup_viewset(model, name, *, search_fields=("name",)):
    """Build a documented viewset for one lookup dimension."""
    plural = name.replace("_", " ")
    return extend_schema_view(
        list=extend_schema(
            tags=["lookups"],
            summary=f"List {plural}",
            description=(
                f"Cursor-paged {plural} for a filter widget, 25 per page, "
                "ordered by name. Pass ?search= to narrow the list."
            ),
        ),
        retrieve=extend_schema(tags=["lookups"], summary=f"Retrieve one of the {plural}"),
    )(
        type(
            f"{model.__name__}LookupViewSet",
            (LookupViewSet,),
            {"model": model, "search_fields": list(search_fields)},
        )
    )


IndustryLookupViewSet = lookup_viewset(Industry, "industries")
SkillLookupViewSet = lookup_viewset(Skill, "skills")
InterestLookupViewSet = lookup_viewset(Interest, "interests")
LanguageLookupViewSet = lookup_viewset(Language, "languages")
CertificationLookupViewSet = lookup_viewset(
    Certification, "certifications", search_fields=("name", "organization")
)
CompanyLookupViewSet = lookup_viewset(Company, "companies")
OccupationRoleLookupViewSet = lookup_viewset(OccupationRole, "occupation_roles",
                                             search_fields=("title",))
OccupationLevelLookupViewSet = lookup_viewset(OccupationLevel, "occupation_levels",
                                              search_fields=("title",))
