from django.db import IntegrityError, transaction
from django.test import TestCase

from social_api.models import EmailType, GenderType, ImportBatch, Personality, PhoneType, User


class EnumTests(TestCase):
    def test_gender_type_values(self):
        self.assertEqual(
            [c[0] for c in GenderType.choices], ["male", "female", "other", "unknown"]
        )

    def test_email_type_values(self):
        self.assertEqual(
            [c[0] for c in EmailType.choices],
            ["personal", "professional", "current_professional", "disposable", "other"],
        )

    def test_phone_type_values(self):
        self.assertEqual([c[0] for c in PhoneType.choices], ["mobile", "home", "work", "other"])

    def test_personality_still_exposes_gender_type(self):
        self.assertIs(Personality.GenderType, GenderType)
        self.assertEqual(Personality._meta.get_field("gender").default, GenderType.UNKNOWN)


class UserAndImportBatchTests(TestCase):
    def test_user_email_is_unique(self):
        User.objects.create_user(email="ada@example.com", password="pw", name="Ada")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email="ada@example.com", password="pw", name="Other")

    def test_user_optionally_self_links_to_a_personality(self):
        person = Personality.objects.create(first_name="Ada", last_name="Lovelace")
        user = User.objects.create_user(
            email="ada@example.com", password="pw", name="Ada", personality=person
        )

        self.assertEqual(person.users.get(), user)

        unlinked = User.objects.create_user(email="bob@example.com", password="pw", name="Bob")
        self.assertIsNone(unlinked.personality)

    def test_import_batch_links_user_and_personalities(self):
        user = User.objects.create_user(email="ada@example.com", password="pw", name="Ada")
        batch = ImportBatch.objects.create(
            user=user, source="people-data-labs", filename="batch1.json", row_count=100
        )
        person = Personality.objects.create(
            first_name="Grace", last_name="Hopper", import_batch=batch
        )

        self.assertEqual(user.import_batches.get(), batch)
        self.assertEqual(batch.personalities.get(), person)

    def test_import_batch_survives_user_deletion(self):
        user = User.objects.create_user(email="ada@example.com", password="pw", name="Ada")
        batch = ImportBatch.objects.create(user=user, source="pdl", filename="b.json", row_count=1)

        user.delete()
        batch.refresh_from_db()

        self.assertIsNone(batch.user)
