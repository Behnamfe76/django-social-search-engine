import unittest

from django.test import SimpleTestCase, TestCase

from social_api.models import Company
from social_api.services import build_slug, build_unique_slug
from social_api.tests.support import tables_exist


class BuildSlugTests(SimpleTestCase):
    def test_slugifies_plain_text(self):
        self.assertEqual(build_slug("Analytical Engines Ltd."), "analytical-engines-ltd")

    def test_collapses_punctuation_and_case(self):
        self.assertEqual(build_slug("  ACME & Co --- Inc!  "), "acme-co-inc")

    def test_truncates_without_trailing_separator(self):
        # A naive cut at 10 would give "acme-corp-", which is not a valid slug tail.
        self.assertEqual(build_slug("Acme Corp Holdings", max_length=10), "acme-corp")

    def test_truncation_is_a_no_op_when_it_fits(self):
        self.assertEqual(build_slug("Acme", max_length=255), "acme")

    def test_allow_unicode_keeps_non_ascii(self):
        self.assertEqual(build_slug("Zürich Größe", allow_unicode=True), "zürich-größe")

    def test_non_unicode_mode_transliterates_away_non_ascii(self):
        self.assertEqual(build_slug("Zürich"), "zurich")

    def test_raises_when_nothing_slugifiable(self):
        for value in ["!!!", "   ", "", None]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    build_slug(value)

    def test_falls_back_when_provided(self):
        self.assertEqual(build_slug("!!!", fallback="Unknown Company"), "unknown-company")

    def test_raises_when_fallback_is_also_unusable(self):
        with self.assertRaises(ValueError):
            build_slug("!!!", fallback="???")


@unittest.skipUnless(tables_exist("companies"), "companies table has no migration yet")
class BuildUniqueSlugTests(TestCase):
    def _company(self, name, slug):
        return Company.objects.create(name=name, slug=slug)

    def test_returns_base_slug_when_free(self):
        self.assertEqual(build_unique_slug("Acme Corp", model=Company), "acme-corp")

    def test_appends_suffix_on_collision(self):
        self._company("Acme Corp", "acme-corp")
        self.assertEqual(build_unique_slug("Acme Corp", model=Company), "acme-corp-2")

    def test_walks_past_consecutive_collisions(self):
        self._company("Acme Corp", "acme-corp")
        self._company("Acme Corp", "acme-corp-2")
        self._company("Acme Corp", "acme-corp-3")
        self.assertEqual(build_unique_slug("Acme Corp", model=Company), "acme-corp-4")

    def test_prefix_sharing_company_does_not_steal_the_base_slug(self):
        self._company("Acme Corporation Global", "acme-corporation-global")
        self.assertEqual(build_unique_slug("Acme Corp", model=Company), "acme-corp")

    def test_instance_does_not_collide_with_itself(self):
        company = self._company("Acme Corp", "acme-corp")
        self.assertEqual(
            build_unique_slug("Acme Corp", model=Company, instance=company),
            "acme-corp",
        )

    def test_queryset_scopes_the_collision_search(self):
        self._company("Acme Corp", "acme-corp")
        scoped = Company.objects.filter(name="Something Else")
        self.assertEqual(
            build_unique_slug("Acme Corp", model=Company, queryset=scoped),
            "acme-corp",
        )

    def test_max_length_defaults_to_the_model_field(self):
        long_name = "a" * 400
        slug = build_unique_slug(long_name, model=Company)
        self.assertEqual(len(slug), Company._meta.get_field("slug").max_length)

    def test_suffixed_slug_still_fits_max_length(self):
        long_name = "a" * 400
        first = build_unique_slug(long_name, model=Company)
        self._company("Long", first)

        second = build_unique_slug(long_name, model=Company)

        self.assertNotEqual(second, first)
        self.assertLessEqual(len(second), Company._meta.get_field("slug").max_length)
        self.assertTrue(second.endswith("-2"))

    def test_generated_slug_actually_saves(self):
        self._company("Acme Corp", "acme-corp")
        slug = build_unique_slug("Acme Corp", model=Company)
        Company.objects.create(name="Acme Corp", slug=slug)
        self.assertEqual(Company.objects.filter(name="Acme Corp").count(), 2)
