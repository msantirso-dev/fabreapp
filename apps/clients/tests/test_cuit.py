from django.test import SimpleTestCase

from apps.clients.cuit_lookup import format_cuit, is_valid_cuit, normalize_cuit


class CuitValidationTests(SimpleTestCase):
    def test_normalize_and_format(self):
        self.assertEqual(normalize_cuit("20-11111111-2"), "20111111112")
        self.assertEqual(format_cuit("20111111112"), "20-11111111-2")

    def test_valid_cuit_checksum(self):
        self.assertTrue(is_valid_cuit("20-11111111-2"))
        self.assertTrue(is_valid_cuit("20111111112"))

    def test_invalid_cuit(self):
        self.assertFalse(is_valid_cuit("30-12345678-0"))
        self.assertFalse(is_valid_cuit("123"))
