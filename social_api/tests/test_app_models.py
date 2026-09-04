import unittest

from django.db import IntegrityError, transaction
from django.test import TestCase

from social_api.models import EmailType, GenderType, ImportBatch, Personality, PhoneType, User
from social_api.tests.support import tables_exist


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


@unittest.skipUnless(tables_exist("users", "import_batches"), "app tables have no migration yet")
class UserAndImportBatchTests(TestCase):
    def test_user_email_is_unique(self):
        User.objects.create(name="Ada", email="ada@example.com", password_hash="x")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create(name="Other", email="ada@example.com", password_hash="y")

    def test_user_optionally_self_links_to_a_personality(self):
        person = Personality.objects.create(first_name="Ada", last_name="Lovelace")
        user = User.objects.create(
            name="Ada", email="ada@example.com", password_hash="x", personality=person
        )

        self.assertEqual(person.users.get(), user)

        unlinked = User.objects.create(name="Bob", email="bob@example.com", password_hash="x")
        self.assertIsNone(unlinked.personality)

    def test_import_batch_links_user_and_personalities(self):
        user = User.objects.create(name="Ada", email="ada@example.com", password_hash="x")
        batch = ImportBatch.objects.create(
            user=user, source="people-data-labs", filename="batch1.json", row_count=100
        )
        person = Personality.objects.create(
            first_name="Grace", last_name="Hopper", import_batch=batch
        )

        self.assertEqual(user.import_batches.get(), batch)
        self.assertEqual(batch.personalities.get(), person)

    def test_import_batch_survives_user_deletion(self):
        user = User.objects.create(name="Ada", email="ada@example.com", password_hash="x")
        batch = ImportBatch.objects.create(user=user, source="pdl", filename="b.json", row_count=1)

        user.delete()
        batch.refresh_from_db()

        self.assertIsNone(batch.user)
