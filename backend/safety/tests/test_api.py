import uuid

from django.utils.dateparse import parse_datetime

from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user, throttle_rates
from safety.models import Block, Report


class BlockListTests(APITestCase):
    url = "/api/blocks/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def test_lists_users_i_blocked(self):
        blocked = make_user(display_name="Annoying")
        block = Block.objects.create(blocker=self.user, blocked=blocked)
        Block.objects.create(blocker=make_user(), blocked=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["user"], {"id": str(blocked.id), "display_name": "Annoying", "major": "", "year": ""})
        self.assertEqual(parse_datetime(body[0]["created_at"]), block.created_at)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 401)


class BlockCreateTests(APITestCase):
    url = "/api/blocks/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())
        self.other = make_user()

    def block(self, user_id):
        return self.client.post(self.url, {"user": str(user_id)}, format="json")

    def test_blocks_user(self):
        response = self.block(self.other.id)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Block.objects.filter(blocker=self.user, blocked=self.other).exists())
        self.assertEqual(response.json()["user"]["id"], str(self.other.id))

    def test_blocking_twice_is_harmless(self):
        self.block(self.other.id)

        response = self.block(self.other.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Block.objects.count(), 1)

    def test_cancels_pending_requests_between_the_two_users(self):
        mine = make_opportunity(owner=self.user)
        theirs = make_opportunity(owner=self.other)
        incoming = ConnectionRequest.objects.create(opportunity=mine, kind="join", sender=self.other, recipient=self.user)
        outgoing = ConnectionRequest.objects.create(opportunity=theirs, kind="join", sender=self.user, recipient=self.other)
        unrelated = ConnectionRequest.objects.create(opportunity=mine, kind="join", sender=make_user(), recipient=self.user)

        self.block(self.other.id)

        for request in (incoming, outgoing, unrelated):
            request.refresh_from_db()
        self.assertEqual(incoming.status, "cancelled")
        self.assertEqual(outgoing.status, "cancelled")
        self.assertEqual(unrelated.status, "pending")

    def test_cannot_block_self(self):
        self.assertEqual(self.block(self.user.id).status_code, 400)

    def test_unknown_user_is_rejected(self):
        self.assertEqual(self.block(uuid.uuid4()).status_code, 400)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.block(self.other.id).status_code, 401)


class BlockDeleteTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())
        self.other = make_user()

    def unblock(self, user_id):
        return self.client.delete(f"/api/blocks/{user_id}/")

    def test_unblocks_user(self):
        Block.objects.create(blocker=self.user, blocked=self.other)

        response = self.unblock(self.other.id)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Block.objects.exists())

    def test_cannot_remove_a_block_made_by_someone_else(self):
        Block.objects.create(blocker=self.other, blocked=self.user)

        self.assertEqual(self.unblock(self.other.id).status_code, 404)
        self.assertTrue(Block.objects.exists())

    def test_not_blocked_is_404(self):
        self.assertEqual(self.unblock(self.other.id).status_code, 404)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.unblock(self.other.id).status_code, 401)


class ReportCreateTests(APITestCase):
    url = "/api/reports/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())
        self.other = make_user()

    def report(self, **data):
        payload = {"reported_user": str(self.other.id), "reason": "spam"}
        payload.update(data)
        return self.client.post(self.url, payload, format="json")

    def test_files_report(self):
        response = self.report(details="Posting ads")

        self.assertEqual(response.status_code, 201)
        report = Report.objects.get()
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.reported_user, self.other)
        self.assertEqual(report.reason, "spam")
        self.assertEqual(report.details, "Posting ads")
        self.assertEqual(report.status, "open")
        self.assertEqual(response.json(), {"id": str(report.id), "status": "open"})

    def test_can_reference_the_reported_users_opportunity(self):
        opportunity = make_opportunity(owner=self.other)

        response = self.report(opportunity=str(opportunity.id))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Report.objects.get().opportunity, opportunity)

    def test_opportunity_must_belong_to_reported_user(self):
        response = self.report(opportunity=str(make_opportunity().id))

        self.assertEqual(response.status_code, 400)

    def test_cannot_report_self(self):
        self.assertEqual(self.report(reported_user=str(self.user.id)).status_code, 400)

    def test_rejects_unknown_reason(self):
        self.assertEqual(self.report(reason="vibes").status_code, 400)

    def test_unknown_user_is_rejected(self):
        self.assertEqual(self.report(reported_user=str(uuid.uuid4())).status_code, 400)

    @throttle_rates(report="2/day")
    def test_rate_limited(self):
        self.report()
        self.report()

        self.assertEqual(self.report().status_code, 429)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.report().status_code, 401)
