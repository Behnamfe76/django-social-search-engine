from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from social_api.tests.support import authenticate

User = get_user_model()


class RegisterTests(APITestCase):
    url = "/api/v1/auth/register/"

    def test_register_creates_a_user_with_a_hashed_password(self):
        response = self.client.post(
            self.url,
            {"name": "Ada", "email": "ada@example.com", "password": "sup3rsecret"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="ada@example.com")
        self.assertNotEqual(user.password, "sup3rsecret")
        self.assertTrue(user.check_password("sup3rsecret"))
        self.assertNotIn("password", response.data)

    def test_password_is_stored_in_the_password_hash_column(self):
        self.client.post(
            self.url,
            {"name": "Ada", "email": "ada@example.com", "password": "sup3rsecret"},
            format="json",
        )
        self.assertEqual(User._meta.get_field("password").column, "password_hash")

    def test_short_password_is_rejected(self):
        response = self.client.post(
            self.url,
            {"name": "Ada", "email": "ada@example.com", "password": "short"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(email="ada@example.com", password="sup3rsecret", name="Ada")

        response = self.client.post(
            self.url,
            {"name": "Other", "email": "ada@example.com", "password": "sup3rsecret"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    url = "/api/v1/auth/login/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="ada@example.com", password="sup3rsecret", name="Ada"
        )

    def test_login_returns_access_and_refresh(self):
        response = self.client.post(
            self.url, {"email": "ada@example.com", "password": "sup3rsecret"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "ada@example.com")

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            self.url, {"email": "ada@example.com", "password": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_soft_deleted_user_cannot_log_in(self):
        from django.utils import timezone

        self.user.deleted_at = timezone.now()
        self.user.save(update_fields=["deleted_at"])

        response = self.client.post(
            self.url, {"email": "ada@example.com", "password": "sup3rsecret"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url, {"email": "ada@example.com", "password": "sup3rsecret"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_a_new_access_token(self):
        login = self.client.post(
            self.url, {"email": "ada@example.com", "password": "sup3rsecret"}, format="json"
        )

        response = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": login.data["refresh"]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_verify_accepts_a_valid_token_and_rejects_junk(self):
        login = self.client.post(
            self.url, {"email": "ada@example.com", "password": "sup3rsecret"}, format="json"
        )

        ok = self.client.post(
            "/api/v1/auth/verify/", {"token": login.data["access"]}, format="json"
        )
        bad = self.client.post("/api/v1/auth/verify/", {"token": "not-a-token"}, format="json")

        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(bad.status_code, status.HTTP_401_UNAUTHORIZED)


class ProtectedRouteTests(APITestCase):
    """Covers JWTRouteAuthMiddleware, which gates whole path prefixes."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="ada@example.com", password="sup3rsecret", name="Ada"
        )

    def test_exempt_route_needs_no_token(self):
        response = self.client.get(reverse("social_api:v1:health-check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_protected_route_without_token_is_401(self):
        response = self.client.get("/api/v1/personalities/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.json())
        self.assertEqual(response["WWW-Authenticate"], 'Bearer realm="api"')

    def test_protected_route_with_token_succeeds(self):
        authenticate(self.client, self.user)

        response = self.client.get("/api/v1/personalities/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_garbage_token_is_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

        response = self.client.get("/api/v1/personalities/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_the_authenticated_user(self):
        authenticate(self.client, self.user)

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "ada@example.com")

    def test_me_without_token_is_401(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MiddlewarePolicyTests(APITestCase):
    """The prefix policy itself, independent of any particular view."""

    def test_is_protected_honours_settings(self):
        from social_api.middleware.auth import JWTRouteAuthMiddleware

        mw = JWTRouteAuthMiddleware(lambda request: None)

        self.assertTrue(mw.is_protected("/api/v1/personalities/"))
        self.assertFalse(mw.is_protected("/api/v1/health/"))
        self.assertFalse(mw.is_protected("/api/v1/auth/login/"))
        self.assertFalse(mw.is_protected("/admin/"))
        self.assertFalse(mw.is_protected("/anything-else/"))

    def test_exempt_prefix_wins_over_protected(self):
        from social_api.middleware.auth import JWTRouteAuthMiddleware

        mw = JWTRouteAuthMiddleware(lambda request: None)
        with self.settings(
            AUTH_PROTECTED_PREFIXES=["/api/"], AUTH_EXEMPT_PREFIXES=["/api/public/"]
        ):
            self.assertTrue(mw.is_protected("/api/private/"))
            self.assertFalse(mw.is_protected("/api/public/thing/"))
