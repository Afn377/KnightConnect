from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from opportunities.models import Opportunity


class DeleteOpportunityTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.login(make_user())
        self.opportunity = make_opportunity(owner=self.owner, title="HackRU Spring Teammates Needed")
        self.member = make_user()
        self.accepted = ConnectionRequest.objects.create(
            opportunity=self.opportunity, kind="join", sender=self.member, recipient=self.owner, status="accepted"
        )
        self.pending = ConnectionRequest.objects.create(
            opportunity=self.opportunity, kind="join", sender=make_user(), recipient=self.owner
        )

    def delete(self, opportunity=None):
        return self.client.delete(f"/api/opportunities/{(opportunity or self.opportunity).id}/")

    def test_owner_deletes_post_and_its_pending_requests(self):
        response = self.delete()

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Opportunity.objects.filter(pk=self.opportunity.pk).exists())
        self.assertFalse(ConnectionRequest.objects.filter(pk=self.pending.pk).exists())

    def test_accepted_connections_remain_with_the_post_title(self):
        self.delete()
        self.login(self.member)

        response = self.client.get(f"/api/requests/{self.accepted.id}/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["opportunity"], {"id": None, "title": "HackRU Spring Teammates Needed", "status": "deleted"})
        self.assertIsNotNone(body["contact_methods"])

    def test_deletes_drafts_too(self):
        draft = make_opportunity(owner=self.owner, status="draft")

        self.assertEqual(self.delete(draft).status_code, 204)

    def test_non_owner_is_forbidden(self):
        self.login(make_user())

        self.assertEqual(self.delete().status_code, 403)
        self.assertTrue(Opportunity.objects.filter(pk=self.opportunity.pk).exists())
