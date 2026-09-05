import datetime

from django.test import SimpleTestCase

from social_api.services.imports import parsing


class TextTests(SimpleTestCase):
    def test_the_export_spellings_of_empty_all_become_none(self):
        for raw in ("", "   ", "None", "null", "nan", "N/A", "-"):
            with self.subTest(raw=raw):
                self.assertIsNone(parsing.text(raw))

    def test_values_are_stripped_and_truncated(self):
        self.assertEqual(parsing.text("  garver  "), "garver")
        self.assertEqual(parsing.text("garver", max_length=3), "gar")


class LiteralTests(SimpleTestCase):
    """The export writes Python literals, not JSON: single quotes and ``None``."""

    def test_python_literal_lists_are_read(self):
        self.assertEqual(
            parsing.string_list("['recruiting', 'leadership']"),
            ["recruiting", "leadership"],
        )

    def test_none_inside_a_literal_is_dropped_from_a_string_list(self):
        self.assertEqual(parsing.string_list("['a', None, '']"), ["a"])

    def test_dict_lists_keep_only_mappings(self):
        self.assertEqual(
            parsing.dict_list("[{'name': 'english'}, 'junk']"), [{"name": "english"}]
        )

    def test_unparseable_cells_are_empty_rather_than_fatal(self):
        self.assertEqual(parsing.string_list("[oops"), [])
        self.assertIsNone(parsing.mapping("{"))


class IntegerTests(SimpleTestCase):
    def test_float_spellings_are_accepted(self):
        self.assertEqual(parsing.integer("3761.0"), 3761)

    def test_a_value_too_large_for_its_column_is_dropped_not_stored(self):
        """Ragged rows shift junk into numeric columns; a DataError would lose the row."""
        self.assertIsNone(parsing.small_integer("999999"))
        self.assertEqual(parsing.small_integer("12"), 12)
        self.assertIsNone(parsing.standard_integer("99999999999"))

    def test_years_outside_a_plausible_range_are_dropped(self):
        self.assertEqual(parsing.year("1919"), 1919)
        self.assertIsNone(parsing.year("19"))
        self.assertIsNone(parsing.year("999999"))


class DateTests(SimpleTestCase):
    def test_partial_dates_resolve_to_their_first_day(self):
        self.assertEqual(parsing.date("2019-10-08"), datetime.date(2019, 10, 8))
        self.assertEqual(parsing.date("2019-10"), datetime.date(2019, 10, 1))
        self.assertEqual(parsing.date("2019"), datetime.date(2019, 1, 1))

    def test_nonsense_is_none(self):
        self.assertIsNone(parsing.date("last tuesday"))


class CoordinateTests(SimpleTestCase):
    def test_a_geo_cell_splits_into_two_decimals(self):
        latitude, longitude = parsing.coordinates("33.21,-97.13")

        self.assertEqual(str(latitude), "33.210000")
        self.assertEqual(str(longitude), "-97.130000")

    def test_impossible_coordinates_are_dropped(self):
        self.assertEqual(parsing.coordinates("999,999"), (None, None))
        self.assertEqual(parsing.coordinates("nowhere"), (None, None))
