from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from catalog.models import Role
from core.testing import APITestCase, make_event, make_user

EASTERN = ZoneInfo("America/New_York")


class PostEventAvailabilityTests(APITestCase):
    url = "/api/opportunities/"

    def setUp(self):
        super().setUp()
        Role.objects.create(name="Backend developer")
        self.login(make_user())
        self.event = make_event(
            name="HackRU Spring",
            starts_at=datetime(2027, 3, 28, 17, tzinfo=EASTERN),
            ends_at=datetime(2027, 3, 30, 15, tzinfo=EASTERN),
            recruiting_ends_at=datetime(2027, 3, 28, 12, tzinfo=EASTERN),
        )

    def post(self, windows, **overrides):
        data = {
            "title": "HackRU Spring Teammates Needed",
            "opportunity_type": "hackathon",
            "commitment": "partial",
            "event": "hackru-spring",
            "roles": [{"role": "backend-developer"}],
            "expires_at": (timezone.now() + timedelta(days=3)).isoformat(),
            "event_availability": windows,
        }
        data.update(overrides)
        return self.client.post(self.url, data, format="json")

    def test_saves_day_and_time_windows(self):
        windows = [
            {"date": "2027-03-28", "start": None, "end": None},
            {"date": "2027-03-29", "start": "10:00", "end": "18:00"},
        ]

        response = self.post(windows)

        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()["event_availability"], windows)

    def test_defaults_to_no_windows(self):
        self.assertEqual(self.post(None).status_code, 400)
        response = self.client.post(self.url, {**self._base(), "event": "hackru-spring"}, format="json")

        self.assertEqual(response.json()["event_availability"], [])

    def _base(self):
        return {
            "title": "t", "opportunity_type": "hackathon", "commitment": "full",
            "roles": [{"role": "backend-developer"}],
            "expires_at": (timezone.now() + timedelta(days=3)).isoformat(),
        }

    def test_rejects_malformed_windows(self):
        self.assertEqual(self.post([{"date": "March 28"}]).status_code, 400)
        self.assertEqual(self.post([{"date": "2027-03-28", "start": "10:00", "end": None}]).status_code, 400)
        self.assertEqual(self.post([{"date": "2027-03-28", "start": "18:00", "end": "10:00"}]).status_code, 400)
        self.assertEqual(self.post([{"date": "2027-03-28", "start": "25:00", "end": "26:00"}]).status_code, 400)

    def test_dates_must_fall_within_the_event(self):
        response = self.post([{"date": "2027-04-02", "start": None, "end": None}])

        self.assertEqual(response.status_code, 400)
        self.assertIn("event_availability", response.json())

    def test_windows_need_an_event(self):
        response = self.post([{"date": "2027-03-28", "start": None, "end": None}], event=None, opportunity_type="personal_project")

        self.assertEqual(response.status_code, 400)
