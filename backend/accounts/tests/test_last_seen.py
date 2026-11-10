from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from core.testing import APITestCase, make_user


class LastSeenTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def last_seen(self):
        return User.objects.get(pk=self.user.pk).last_seen_at

    def test_signed_in_request_records_last_seen(self):
        self.client.get("/api/me/")

        self.assertIsNotNone(self.last_seen())
        self.assertLess(timezone.now() - self.last_seen(), timedelta(seconds=5))

    def test_recent_activity_is_not_rewritten(self):
        recent = timezone.now() - timedelta(minutes=2)
        User.objects.filter(pk=self.user.pk).update(last_seen_at=recent)

        self.client.get("/api/me/")

        self.assertEqual(self.last_seen(), recent)

    def test_stale_activity_is_refreshed(self):
        stale = timezone.now() - timedelta(minutes=10)
        User.objects.filter(pk=self.user.pk).update(last_seen_at=stale)

        self.client.get("/api/me/")

        self.assertGreater(self.last_seen(), stale)

    def test_anonymous_requests_are_unaffected(self):
        self.client.logout()

        self.assertEqual(self.client.get("/api/health/").status_code, 200)
