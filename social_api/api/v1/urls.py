from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from social_api.api.v1.views import (
    CertificationLookupViewSet,
    CompanyLookupViewSet,
    DashboardView,
    HealthCheckView,
    IndustryLookupViewSet,
    InterestLookupViewSet,
    LanguageLookupViewSet,
    OccupationLevelLookupViewSet,
    OccupationRoleLookupViewSet,
    SkillLookupViewSet,
    ImportBatchViewSet,
    LoginView,
    MeView,
    RegisterView,
)
from social_api.api.v1.views.personality import PersonalityViewSet

app_name = "v1"

router = DefaultRouter()
router.register("personalities", PersonalityViewSet, basename="personality")
router.register("imports", ImportBatchViewSet, basename="import")

# Reference lists for the filter widgets. Read-only, cursor-paged 25 at a time.
router.register("industries", IndustryLookupViewSet, basename="industry")
router.register("skills", SkillLookupViewSet, basename="skill")
router.register("interests", InterestLookupViewSet, basename="interest")
router.register("languages", LanguageLookupViewSet, basename="language")
router.register("certifications", CertificationLookupViewSet, basename="certification")
router.register("companies", CompanyLookupViewSet, basename="company")
router.register(
    "occupation-roles", OccupationRoleLookupViewSet, basename="occupation-role"
)
router.register(
    "occupation-levels", OccupationLevelLookupViewSet, basename="occupation-level"
)

# /auth/ is exempt from JWTRouteAuthMiddleware so tokens can be obtained;
# /auth/me/ re-protects itself with IsAuthenticated.
auth_urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("me/", MeView.as_view(), name="me"),
]

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("auth/", include((auth_urlpatterns, "auth"), namespace="auth")),
    path("", include(router.urls)),
]
