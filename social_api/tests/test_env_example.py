from django.conf import settings
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


class EnvExampleTests(APITestCase):
    """``.env.example`` is copied verbatim by ``./sse init``.

    A wrong value there is not a documentation slip, it is a misconfiguration
    that ships -- and it did: the file predated the documentation routes, so a
    project bootstrapped from it put ``/api/docs/`` behind the JWT gate while
    every developer running without a ``.env`` saw the code default and 200s.
    These tests run the middleware against the values the file actually contains.
    """

    def prefixes_from_example(self, key):
        path = settings.BASE_DIR / ".env.example"
        for line in path.read_text().splitlines():
            if line.startswith(f"{key}="):
                _, _, value = line.partition("=")
                return [item.strip() for item in value.split(",") if item.strip()]
        self.fail(f".env.example does not define {key}")

    def example_settings(self):
        return override_settings(
            AUTH_PROTECTED_PREFIXES=self.prefixes_from_example("AUTH_PROTECTED_PREFIXES"),
            AUTH_EXEMPT_PREFIXES=self.prefixes_from_example("AUTH_EXEMPT_PREFIXES"),
        )

    def test_public_routes_stay_public_under_the_shipped_example(self):
        with self.example_settings():
            for path in ("/api/v1/health/", "/api/schema/", "/api/docs/", "/api/redoc/"):
                with self.subTest(path=path):
                    self.assertEqual(
                        self.client.get(path).status_code, status.HTTP_200_OK
                    )

    def test_the_api_stays_protected_under_the_shipped_example(self):
        with self.example_settings():
            for path in ("/api/v1/personalities/", "/api/v1/imports/"):
                with self.subTest(path=path):
                    self.assertEqual(
                        self.client.get(path).status_code,
                        status.HTTP_401_UNAUTHORIZED,
                    )

    def test_login_is_reachable_so_a_token_can_be_obtained_at_all(self):
        with self.example_settings():
            response = self.client.post("/api/v1/auth/login/", {}, format="json")

            self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
