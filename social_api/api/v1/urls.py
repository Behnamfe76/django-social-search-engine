from django.urls import include, path
from rest_framework.routers import DefaultRouter

from social_api.api.v1.views import HealthCheckView
from social_api.api.v1.views.personality import PersonalityViewSet

app_name = "v1"

router = DefaultRouter()
router.register("personalities", PersonalityViewSet, basename="personality")

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("", include(router.urls)),
]
