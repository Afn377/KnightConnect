from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from connections.models import ConnectionRequest
from core.testing import make_opportunity, make_user


class ExpireOpportunitiesCommandTests(TestCase):
    def run_command(self):
        out = StringIO()
        call_command("expire_opportunities", stdout=out)
        return out.getvalue()

    def test_expires_past_due_opportunities_and_their_pending_requests(self):
        due = make_opportunity(expires_at=timezone.now() - timedelta(minutes=1))
        current = make_opportunity()
        pending = ConnectionRequest.objects.create(opportunity=due, kind="join", sender=make_user(), recipient=due.owner)

        output = self.run_command()

        due.refresh_from_db()
        current.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(due.status, "expired")
        self.assertEqual(due.close_reason, "expired")
        self.assertEqual(current.status, "open")
        self.assertEqual(pending.status, "expired")
        self.assertIn("Expired 1 opportunity", output)

    def test_nothing_to_do(self):
        make_opportunity()

        self.assertIn("Expired 0 opportunities", self.run_command())
