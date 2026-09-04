from django.urls import path

from social_api.api.v1.views import HealthCheckView

app_name = "v1"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
]
