from rest_framework import status
from rest_framework.test import APISimpleTestCase, APITestCase

from social_api.models import Location, Personality, PersonalityLocation


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
        self.assertIn("birth_year", create_response.data)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["full_name"], "Ada Byron Lovelace")
        self.assertNotIn("birth_year", list_response.data["results"][0])

    def test_personality_list_can_be_paginated_from_viewset(self):
        for index in range(3):
            Personality.objects.create(
                first_name=f"First{index}",
                last_name=f"Last{index}",
            )

        response = self.client.get("/api/v1/personalities/?page_size=2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])

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

    def test_retrieve_personality_uses_detail_serializer(self):
        personality = Personality.objects.create(
            first_name="Katherine",
            last_name="Johnson",
            summary="Mathematician",
        )

        response = self.client.get(f"/api/v1/personalities/{personality.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Katherine Johnson")
        self.assertEqual(response.data["summary"], "Mathematician")

    def test_update_personality_regenerates_full_name(self):
        personality = Personality.objects.create(
            first_name="Alan",
            last_name="Turing",
        )

        response = self.client.patch(
            f"/api/v1/personalities/{personality.id}/",
            {
                "middle_initial": "M",
                "full_name": "Ignored Value",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
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

    def test_personality_location_relationships_are_available_from_both_sides(self):
        personality = Personality.objects.create(
            first_name="Mary",
            last_name="Jackson",
        )
        location = Location.objects.create(
            name=Location.LocationName.CITY,
            locality="Hampton",
            region="Virginia",
            country="United States",
        )

        PersonalityLocation.objects.create(
            personality=personality,
            location=location,
            is_primary=True,
        )

        self.assertEqual(list(personality.locations.all()), [location])
        self.assertEqual(list(location.personalities.all()), [personality])
