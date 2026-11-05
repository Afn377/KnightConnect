from datetime import datetime
from zoneinfo import ZoneInfo

from analytics.models import FunnelEvent
from core.testing import APITestCase, make_user

EASTERN = ZoneInfo("America/New_York")


class FunnelReportTests(APITestCase):
    url = "/api/analytics/funnel/"

    def setUp(self):
        super().setUp()
        self.staff = make_user(is_staff=True)

    def event(self, event_type, day, **metadata):
        event = FunnelEvent.record(event_type, **metadata)
        FunnelEvent.objects.filter(pk=event.pk).update(occurred_at=datetime(2026, 11, day, 12, tzinfo=EASTERN))

    def test_counts_each_funnel_step(self):
        for _ in range(4):
            self.event("recommendation_shown", 3)
        for _ in range(3):
            self.event("recommendation_viewed", 3)
        self.event("request_sent", 3)
        self.event("request_sent", 4)
        self.event("request_accepted", 4)
        self.event("connection_rated", 5, was_useful=True)
        self.event("connection_rated", 5, was_useful=False)
        self.event("opportunity_created", 5)
        self.login(self.staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["funnel"],
            {
                "recommendations_shown": 4,
                "recommendations_viewed": 3,
                "requests_sent": 2,
                "requests_accepted": 1,
                "connections_rated": 2,
                "connections_rated_useful": 1,
            },
        )

    def test_limits_to_inclusive_date_range(self):
        self.event("request_sent", 2)
        self.event("request_sent", 3)
        self.event("request_sent", 4)
        self.event("request_sent", 5)
        self.login(self.staff)

        body = self.client.get(self.url, {"start": "2026-11-03", "end": "2026-11-04"}).json()

        self.assertEqual(body["funnel"]["requests_sent"], 2)
        self.assertEqual(body["start"], "2026-11-03")
        self.assertEqual(body["end"], "2026-11-04")

    def test_rejects_invalid_dates(self):
        self.login(self.staff)

        self.assertEqual(self.client.get(self.url, {"start": "yesterday"}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {"start": "2026-11-05", "end": "2026-11-01"}).status_code, 400)

    def test_staff_only(self):
        self.login(make_user())

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
