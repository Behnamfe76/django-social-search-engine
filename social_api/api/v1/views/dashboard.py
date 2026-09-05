from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from social_api.api.v1.serializers import DashboardSerializer
from social_api.selectors.dashboard import dashboard_stats


class DashboardView(APIView):
    """The dashboard's only endpoint: one GET, one snapshot, no parameters.

    Deliberately not a ViewSet -- there is nothing to page, filter or order. The
    payload is the whole set of panels, so the front end makes a single request
    and every tile is drawn from the same consistent read.
    """

    @extend_schema(
        tags=["dashboard"],
        summary="Aggregate statistics for the dashboard",
        description=(
            "Every panel in one payload. Takes no query parameters: the response "
            "is a full-dataset snapshot, not a filtered view."
        ),
        responses=DashboardSerializer,
    )
    def get(self, request):
        return Response(DashboardSerializer(dashboard_stats()).data)
