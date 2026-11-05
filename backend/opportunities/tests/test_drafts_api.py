from datetime import timedelta

from django.utils import timezone

from analytics.models import FunnelEvent
from catalog.models import Role
from core.testing import APITestCase, make_event, make_user
from opportunities.models import Opportunity


class DraftTests(APITestCase):
    url = "/api/opportunities/"

    def setUp(self):
        super().setUp()
        Role.objects.create(name="Backend developer")
        self.owner = self.login(make_user())
        self.event = make_event(name="HackRU Spring")

    def save_draft(self, **data):
        return self.client.post(self.url, {"draft": True, **data}, format="json")

    def complete_fields(self):
        return {
            "title": "HackRU Spring Teammates Needed",
            "opportunity_type": "hackathon",
            "commitment": "full",
            "roles": [{"role": "backend-developer"}],
            "expires_at": (timezone.now() + timedelta(days=3)).isoformat(),
        }

    def test_saves_a_partial_draft(self):
        response = self.save_draft(event="hackru-spring")

        self.assertEqual(response.status_code, 201, response.json())
        body = response.json()
        self.assertEqual(body["status"], "draft")
        self.assertEqual(body["draft_step"], 1)
        self.assertEqual(body["title"], "")
        self.assertEqual(Opportunity.objects.get().status, "draft")
        self.assertFalse(FunnelEvent.objects.exists())

    def test_draft_needs_a_title_or_event(self):
        self.assertEqual(self.save_draft().status_code, 400)
        self.assertEqual(self.save_draft(title="Just a title").status_code, 201)

    def test_drafts_are_private_to_the_owner(self):
        draft_id = self.save_draft(title="Secret").json()["id"]

        self.assertEqual(self.client.get(self.url).json()["count"], 0)
        self.assertEqual(self.client.get(f"{self.url}{draft_id}/").status_code, 200)
        self.assertEqual([item["id"] for item in self.client.get(f"{self.url}mine/", {"status": "draft"}).json()["results"]], [draft_id])

        self.login(make_user())
        self.assertEqual(self.client.get(f"{self.url}{draft_id}/").status_code, 404)

    def test_editing_a_draft_keeps_validation_relaxed(self):
        draft_id = self.save_draft(title="Draft").json()["id"]

        response = self.client.patch(f"{self.url}{draft_id}/", {"project_ideas": "AI tutor", "draft_step": 3}, format="json")

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["draft_step"], 3)
        self.assertEqual(response.json()["status"], "draft")

    def test_drafts_cannot_receive_requests(self):
        draft_id = self.save_draft(**self.complete_fields()).json()["id"]
        self.login(make_user())

        response = self.client.post("/api/requests/", {"opportunity": draft_id}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_publishing_an_incomplete_draft_lists_what_is_missing(self):
        draft_id = self.save_draft(title="Draft").json()["id"]

        response = self.client.post(f"{self.url}{draft_id}/publish/")

        self.assertEqual(response.status_code, 400)
        self.assertTrue({"roles", "expires_at", "opportunity_type", "commitment"} <= set(response.json()))
        self.assertEqual(Opportunity.objects.get().status, "draft")

    def test_publishing_a_complete_draft_opens_it(self):
        draft_id = self.save_draft(**self.complete_fields()).json()["id"]

        response = self.client.post(f"{self.url}{draft_id}/publish/")

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["status"], "open")
        self.assertEqual(self.client.get(self.url).json()["count"], 1)
        self.assertTrue(FunnelEvent.objects.filter(event_type="opportunity_created").exists())

    def test_publishing_rechecks_the_expiry(self):
        draft_id = self.save_draft(**self.complete_fields()).json()["id"]
        Opportunity.objects.filter(pk=draft_id).update(expires_at=timezone.now() - timedelta(hours=1))

        self.assertEqual(self.client.post(f"{self.url}{draft_id}/publish/").status_code, 400)

    def test_only_drafts_can_be_published(self):
        published = self.client.post(self.url, self.complete_fields(), format="json").json()["id"]

        self.assertEqual(self.client.post(f"{self.url}{published}/publish/").status_code, 409)
