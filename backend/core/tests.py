from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .validators import validate_availability_slots


class HealthCheckTests(TestCase):
    def test_health_reports_ok_without_authentication(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})


class AvailabilityValidatorTests(SimpleTestCase):
    def test_accepts_known_unique_slots(self):
        validate_availability_slots(["weekday_evening", "weekend_morning"])
        validate_availability_slots([])

    def test_rejects_non_list(self):
        with self.assertRaises(ValidationError):
            validate_availability_slots("weekday_evening")

    def test_rejects_unknown_slot(self):
        with self.assertRaises(ValidationError):
            validate_availability_slots(["sometime"])

    def test_rejects_duplicates(self):
        with self.assertRaises(ValidationError):
            validate_availability_slots(["weekend_evening", "weekend_evening"])
