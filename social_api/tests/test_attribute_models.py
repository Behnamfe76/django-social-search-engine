import unittest

from django.db import IntegrityError, transaction
from django.test import TestCase

from social_api.models import (
    Certification,
    Interest,
    Language,
    Personality,
    PersonalityCertification,
    PersonalityLanguage,
    Skill,
)
from social_api.tests.support import tables_exist

ATTRIBUTE_TABLES = (
    "skills",
    "personality_skills",
    "interests",
    "personality_interests",
    "languages",
    "personality_languages",
    "certifications",
    "personality_certifications",
)


@unittest.skipUnless(tables_exist(*ATTRIBUTE_TABLES), "attribute tables have no migration yet")
class PersonalityAttributeTests(TestCase):
    def setUp(self):
        self.person = Personality.objects.create(first_name="Ada", last_name="Lovelace")

    def test_skills_m2m_traverses_the_composite_pk_join_table(self):
        python = Skill.objects.create(name="Python", slug="python")
        sql = Skill.objects.create(name="SQL", slug="sql")

        self.person.skills.add(python, sql)

        self.assertCountEqual(self.person.skills.all(), [python, sql])
        self.assertEqual(python.personalities.get(), self.person)
        self.assertEqual(self.person.skill_links.count(), 2)

    def test_interests_m2m_round_trips(self):
        chess = Interest.objects.create(name="Chess", slug="chess")
        self.person.interests.add(chess)

        self.assertEqual(self.person.interests.get(), chess)
        self.assertEqual(chess.personalities.get(), self.person)

    def test_language_link_carries_proficiency(self):
        french = Language.objects.create(name="French", code="fr", slug="french")
        PersonalityLanguage.objects.create(
            personality=self.person, language=french, proficiency=4
        )

        link = self.person.language_links.get()
        self.assertEqual(link.pk, (self.person.pk, french.pk))
        self.assertEqual(link.proficiency, 4)
        self.assertEqual(self.person.languages.get(), french)

    def test_same_skill_cannot_be_attached_twice(self):
        python = Skill.objects.create(name="Python", slug="python")
        self.person.skills.add(python)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.person.skill_links.create(skill=python)

    def test_certification_is_unique_per_person_and_start_date(self):
        cert = Certification.objects.create(
            name="AWS Architect", slug="aws-architect", organization="Amazon"
        )
        PersonalityCertification.objects.create(personality=self.person, certification=cert)

        # NULL start_date must still collide (nulls_distinct=False)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PersonalityCertification.objects.create(
                    personality=self.person, certification=cert
                )

    def test_same_certification_with_a_different_start_date_is_allowed(self):
        cert = Certification.objects.create(name="AWS Architect", slug="aws-architect")
        PersonalityCertification.objects.create(
            personality=self.person, certification=cert, start_date="2020-01-01"
        )
        PersonalityCertification.objects.create(
            personality=self.person, certification=cert, start_date="2023-01-01"
        )

        self.assertEqual(self.person.certification_links.count(), 2)
        self.assertEqual(self.person.certifications.count(), 2)
