import unittest
from src.normalization import (
    normalize_email, normalize_phone, normalize_date, 
    normalize_country, normalize_skill, parse_location
)

class TestNormalization(unittest.TestCase):
    def test_email(self):
        self.assertEqual(normalize_email("  Rohan.Pagadala15@Gmail.Com  "), "rohan.pagadala15@gmail.com")
        self.assertIsNone(normalize_email("not-an-email"))

    def test_phone(self):
        self.assertEqual(normalize_phone("9876543210"), "+919876543210")
        self.assertEqual(normalize_phone("+91 98765 43210"), "+919876543210")
        self.assertEqual(normalize_phone("+1-234-567-8901"), "+12345678901")

    def test_date(self):
        self.assertEqual(normalize_date("Jan 2025"), "2025-01")
        self.assertEqual(normalize_date("02/2021"), "2021-02")
        self.assertEqual(normalize_date("2026-07"), "2026-07")
        self.assertEqual(normalize_date("present"), "Present")
        self.assertEqual(normalize_date("2022"), "2022-01")

    def test_country(self):
        self.assertEqual(normalize_country("India"), "IN")
        self.assertEqual(normalize_country("United States"), "US")
        self.assertEqual(normalize_country("US"), "US")

    def test_skill(self):
        self.assertEqual(normalize_skill("ML"), "Machine Learning")
        self.assertEqual(normalize_skill("deep learning"), "Deep Learning")
        self.assertEqual(normalize_skill("Python"), "Python")

    def test_location(self):
        loc = parse_location("Hyderabad, TG, India")
        self.assertEqual(loc["city"], "Hyderabad")
        self.assertEqual(loc["region"], "TG")
        self.assertEqual(loc["country"], "IN")

if __name__ == "__main__":
    unittest.main()
