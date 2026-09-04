from rest_framework import status
from rest_framework.test import APISimpleTestCase


class HealthCheckApiTests(APISimpleTestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "service": "social_api",
            },
        )
