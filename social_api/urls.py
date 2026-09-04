from django.urls import include, path

app_name = "social_api"

urlpatterns = [
    path("v1/", include("social_api.api.v1.urls")),
]
