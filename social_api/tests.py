from rest_framework import status
from rest_framework.test import APISimpleTestCase, APITestCase

from social_api.models import Personality


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


class PersonalityApiTests(APITestCase):
    def test_can_create_and_list_personality(self):
        payload = {
            "first_name": "Ada",
            "middle_name": "Byron",
            "last_name": "Lovelace",
            "gender": "female",
            "birth_year": 1815,
            "version_status": {"source": "seed"},
        }

        create_response = self.client.post(
            "/api/v1/personalities/",
            payload,
            format="json",
        )
        list_response = self.client.get("/api/v1/personalities/")

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["full_name"], "Ada Byron Lovelace")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["full_name"], "Ada Byron Lovelace")

    def test_full_name_is_generated_and_ignores_input(self):
        response = self.client.post(
            "/api/v1/personalities/",
            {
                "first_name": "Alan",
                "middle_initial": "M",
                "last_name": "Turing",
                "full_name": "Wrong Name",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["full_name"], "Alan M Turing")

    def test_delete_soft_deletes_personality(self):
        personality = Personality.objects.create(
            first_name="Grace",
            last_name="Hopper",
        )

        response = self.client.delete(f"/api/v1/personalities/{personality.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        personality.refresh_from_db()
        self.assertIsNotNone(personality.deleted_at)
        self.assertEqual(Personality.objects.filter(deleted_at__isnull=True).count(), 0)
