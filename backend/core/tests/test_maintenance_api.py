from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from accounts.models import LoginCode, User
from analytics.models import FunnelEvent
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from opportunities.models import Opportunity

SECRET = "test-cron-secret"


@override_settings(CRON_SECRET=SECRET)
class MaintenanceTests(APITestCase):
    url = "/api/internal/maintenance/"

    def run_job(self, secret=SECRET, method="get"):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {secret}"} if secret else {}
        return getattr(self.client, method)(self.url, **headers)

    def test_expires_opportunities_past_their_deadline(self):
        past = make_opportunity(expires_at=timezone.now() - timedelta(minutes=1))
        current = make_opportunity()
        pending = ConnectionRequest.objects.create(opportunity=past, kind="join", sender=make_user(), recipient=past.owner)

        response = self.run_job()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["expired_opportunities"], 1)
        past.refresh_from_db()
        current.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(past.status, "expired")
        self.assertEqual(past.close_reason, "expired")
        self.assertEqual(current.status, "open")
        self.assertEqual(pending.status, "expired")
        self.assertTrue(FunnelEvent.objects.filter(event_type="opportunity_closed", opportunity=past).exists())

    def test_permanently_deletes_accounts_after_grace_period(self):
        due = make_user(deletion_scheduled_for=timezone.now() - timedelta(minutes=1))
        waiting = make_user(deletion_scheduled_for=timezone.now() + timedelta(days=1))
        make_opportunity(owner=due)
        FunnelEvent.record(FunnelEvent.Type.OPPORTUNITY_VIEWED, user=due)

        response = self.run_job()

        self.assertEqual(response.json()["deleted_accounts"], 1)
        self.assertFalse(User.objects.filter(pk=due.pk).exists())
        self.assertTrue(User.objects.filter(pk=waiting.pk).exists())
        self.assertFalse(Opportunity.objects.filter(owner_id=due.pk).exists())
        self.assertIsNone(FunnelEvent.objects.get(event_type="opportunity_viewed").user)

    def test_purges_old_login_codes(self):
        LoginCode.objects.create(email="old@rutgers.edu", code_hash="x", expires_at=timezone.now() - timedelta(days=2))
        LoginCode.objects.create(email="new@rutgers.edu", code_hash="y", expires_at=timezone.now() + timedelta(minutes=5))

        response = self.run_job()

        self.assertEqual(response.json()["purged_login_codes"], 1)
        self.assertEqual(list(LoginCode.objects.values_list("email", flat=True)), ["new@rutgers.edu"])

    def test_accepts_post(self):
        self.assertEqual(self.run_job(method="post").status_code, 200)

    def test_rejects_missing_or_wrong_secret(self):
        self.assertEqual(self.run_job(secret=None).status_code, 403)
        self.assertEqual(self.run_job(secret="wrong").status_code, 403)

    @override_settings(CRON_SECRET="")
    def test_disabled_when_no_secret_is_configured(self):
        self.assertEqual(self.run_job(secret="").status_code, 403)
        self.assertEqual(self.run_job(secret="anything").status_code, 403)
