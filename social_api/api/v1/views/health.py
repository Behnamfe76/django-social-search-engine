from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from social_api.api.v1.serializers import HealthCheckSerializer


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["health"],
        summary="Service liveness",
        responses=HealthCheckSerializer,
        auth=[],
    )
    def get(self, request):
        serializer = HealthCheckSerializer(
            {
                "status": "ok",
                "service": "social_api",
            }
        )
        return Response(serializer.data)
