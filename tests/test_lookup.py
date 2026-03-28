import unittest

from lookup import extract_number, lookup_name, normalize_number


class LookupTests(unittest.TestCase):
    def test_extracts_plain_local_number(self):
        self.assertEqual(extract_number("check number 0244123456 for me"), "0244123456")

    def test_extracts_number_with_spaces(self):
        self.assertEqual(extract_number("024 412 3456"), "0244123456")

    def test_normalizes_international_number(self):
        self.assertEqual(normalize_number("+233244123456"), "0244123456")

    def test_lookup_finds_known_number(self):
        self.assertEqual(lookup_name("0244123456"), "Kofi Mensah")

    def test_lookup_returns_none_for_unknown_number(self):
        self.assertIsNone(lookup_name("0240000000"))


if __name__ == "__main__":
    unittest.main()
