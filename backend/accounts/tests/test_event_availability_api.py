from datetime import datetime
from zoneinfo import ZoneInfo

from core.testing import APITestCase, make_event, make_user

EASTERN = ZoneInfo("America/New_York")


class ProfileEventAvailabilityTests(APITestCase):
    url = "/api/me/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())
        self.hackru = make_event(
            name="HackRU Spring",
            starts_at=datetime(2027, 3, 28, 17, tzinfo=EASTERN),
            ends_at=datetime(2027, 3, 30, 15, tzinfo=EASTERN),
            recruiting_ends_at=datetime(2027, 3, 28, 12, tzinfo=EASTERN),
        )
        self.princeton = make_event(name="HackPrinceton Spring")

    def patch(self, data):
        return self.client.patch(self.url, data, format="json")

    def test_sets_availability_for_each_interested_event(self):
        response = self.patch(
            {
                "event_availability": [
                    {"event": "hackru-spring", "full_event": False, "windows": [{"date": "2027-03-29", "start": "09:00", "end": "15:00"}]},
                    {"event": "hackprinceton-spring", "full_event": True, "windows": []},
                ]
            }
        )

        self.assertEqual(response.status_code, 200, response.json())
        body = response.json()
        self.assertEqual(
            sorted(body["event_availability"], key=lambda entry: entry["event"]["slug"]),
            [
                {"event": {"slug": "hackprinceton-spring", "name": "HackPrinceton Spring"}, "full_event": True, "windows": []},
                {
                    "event": {"slug": "hackru-spring", "name": "HackRU Spring"},
                    "full_event": False,
                    "windows": [{"date": "2027-03-29", "start": "09:00", "end": "15:00"}],
                },
            ],
        )
        self.assertEqual(sorted(e["slug"] for e in body["interested_events"]), ["hackprinceton-spring", "hackru-spring"])

    def test_interested_events_default_to_the_full_event(self):
        self.patch({"interested_events": ["hackru-spring"]})

        entry = self.client.get(self.url).json()["event_availability"][0]

        self.assertEqual((entry["full_event"], entry["windows"]), (True, []))

    def test_keeps_availability_when_interested_events_are_resaved(self):
        self.patch({"event_availability": [{"event": "hackru-spring", "full_event": False, "windows": [{"date": "2027-03-28", "start": None, "end": None}]}]})

        self.patch({"interested_events": ["hackru-spring", "hackprinceton-spring"]})

        entries = {e["event"]["slug"]: e for e in self.client.get(self.url).json()["event_availability"]}
        self.assertFalse(entries["hackru-spring"]["full_event"])
        self.assertTrue(entries["hackprinceton-spring"]["full_event"])

    def test_windows_must_fall_on_event_dates(self):
        response = self.patch(
            {"event_availability": [{"event": "hackru-spring", "full_event": False, "windows": [{"date": "2027-05-01", "start": None, "end": None}]}]}
        )

        self.assertEqual(response.status_code, 400)

    def test_partial_availability_needs_windows(self):
        response = self.patch({"event_availability": [{"event": "hackru-spring", "full_event": False, "windows": []}]})

        self.assertEqual(response.status_code, 400)

    def test_public_profile_shows_event_availability(self):
        other = make_user()
        self.login(other)
        self.patch({"interested_events": ["hackru-spring"]})
        self.login(self.user)

        body = self.client.get(f"/api/users/{other.id}/").json()

        self.assertEqual(body["event_availability"][0]["full_event"], True)
