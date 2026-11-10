from datetime import timedelta

from django.utils import timezone

from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from opportunities.models import Opportunity


class PostCountsTests(APITestCase):
    url = "/api/opportunities/mine/"

    def setUp(self):
        super().setUp()
        self.owner = self.login(make_user())
        self.active = make_opportunity(owner=self.owner, title="Active")
        self.past_due = make_opportunity(owner=self.owner, title="Past due", expires_at=timezone.now() - timedelta(hours=1))
        self.expired = make_opportunity(owner=self.owner, title="Expired")
        self.expired.close(Opportunity.CloseReason.EXPIRED)
        self.closed = make_opportunity(owner=self.owner, title="Closed")
        self.closed.close(Opportunity.CloseReason.OWNER_CLOSED)
        self.draft = make_opportunity(owner=self.owner, title="Draft", status="draft")
        make_opportunity(title="Someone else's")

    def titles(self, **params):
        return {item["title"] for item in self.client.get(self.url, params).json()["results"]}

    def test_reports_counts_for_each_tab(self):
        body = self.client.get(self.url).json()

        self.assertEqual(body["counts"], {"all": 5, "active": 1, "closed": 1, "expired": 2, "draft": 1})

    def test_tabs_filter_by_effective_status(self):
        self.assertEqual(self.titles(status="active"), {"Active"})
        self.assertEqual(self.titles(status="expired"), {"Past due", "Expired"})
        self.assertEqual(self.titles(status="closed"), {"Closed"})
        self.assertEqual(self.titles(status="draft"), {"Draft"})

    def test_owner_sees_pending_and_confirmed_counts(self):
        for status in ("pending", "pending", "accepted", "declined"):
            ConnectionRequest.objects.create(
                opportunity=self.active, kind="join", sender=make_user(), recipient=self.owner, status=status
            )

        item = next(i for i in self.client.get(self.url).json()["results"] if i["title"] == "Active")

        self.assertEqual(item["pending_requests"], 2)
        self.assertEqual(item["confirmed"], 2)

    def test_pending_count_is_hidden_from_others(self):
        self.login(make_user())

        item = self.client.get(f"/api/opportunities/{self.active.id}/").json()

        self.assertIsNone(item["pending_requests"])
        self.assertEqual(item["confirmed"], 1)
