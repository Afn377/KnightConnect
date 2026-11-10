import re
from datetime import timedelta

from django.core import mail
from django.utils import timezone

from accounts.models import User
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user


class AccountDeletionTests(APITestCase):
    url = "/api/me/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user("netid@rutgers.edu"))

    def test_schedules_deletion_after_three_day_grace_period(self):
        before = timezone.now()

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 202)
        self.user.refresh_from_db()
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertGreaterEqual(self.user.deletion_scheduled_for, before + timedelta(days=3))
        self.assertLessEqual(self.user.deletion_scheduled_for, timezone.now() + timedelta(days=3))
        self.assertIn("deletion_scheduled_for", response.json())

    def test_signs_the_user_out(self):
        self.client.delete(self.url)

        self.assertNotIn("_auth_user_id", self.client.session)

    def test_emails_the_user_about_recovery(self):
        self.client.delete(self.url)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["netid@rutgers.edu"])
        self.assertIn("3 days", message.body)
        self.assertIn("sign in", message.body.lower())

    def test_cancels_pending_requests_both_ways(self):
        own = make_opportunity(owner=self.user)
        other = make_opportunity()
        incoming = ConnectionRequest.objects.create(
            opportunity=own, kind="join", sender=make_user(), recipient=self.user
        )
        outgoing = ConnectionRequest.objects.create(
            opportunity=other, kind="join", sender=self.user, recipient=other.owner
        )
        accepted = ConnectionRequest.objects.create(
            opportunity=other, kind="invite", sender=other.owner, recipient=self.user, status="accepted"
        )

        self.client.delete(self.url)

        for request in (incoming, outgoing, accepted):
            request.refresh_from_db()
        self.assertEqual(incoming.status, "cancelled")
        self.assertEqual(outgoing.status, "cancelled")
        self.assertEqual(accepted.status, "accepted")

    def test_signing_in_during_grace_period_restores_account(self):
        self.client.delete(self.url)
        self.client.post("/api/auth/request-code/", {"email": "netid@rutgers.edu"}, format="json")
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

        response = self.client.post("/api/auth/verify-code/", {"email": "netid@rutgers.edu", "code": code}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["restored"])
        self.user.refresh_from_db()
        self.assertIsNone(self.user.deletion_scheduled_for)

    def test_normal_sign_in_is_not_a_restore(self):
        self.client.logout()
        self.client.post("/api/auth/request-code/", {"email": "netid@rutgers.edu"}, format="json")
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

        response = self.client.post("/api/auth/verify-code/", {"email": "netid@rutgers.edu", "code": code}, format="json")

        self.assertFalse(response.json()["restored"])

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.delete(self.url).status_code, 401)
