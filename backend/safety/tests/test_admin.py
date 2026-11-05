from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from connections.models import ConnectionRequest
from core.testing import make_opportunity, make_user
from safety.models import Report


class ReportModerationActionTests(TestCase):
    def setUp(self):
        self.moderator = User.objects.create_superuser("mod@rutgers.edu", "a-strong-password-123")
        self.client.force_login(self.moderator)
        self.owner = make_user()
        self.opportunity = make_opportunity(owner=self.owner)
        self.pending = ConnectionRequest.objects.create(
            opportunity=self.opportunity, kind="join", sender=make_user(), recipient=self.owner
        )
        self.report = Report.objects.create(
            reporter=make_user(), reported_user=self.owner, opportunity=self.opportunity, reason="spam"
        )
        self.no_opportunity = Report.objects.create(reporter=make_user(), reported_user=self.owner, reason="spam")

    def run_action(self, *reports):
        return self.client.post(
            reverse("admin:safety_report_changelist"),
            {"action": "close_reported_opportunities", "_selected_action": [str(r.pk) for r in reports]},
            follow=True,
        )

    def test_closes_reported_opportunity_and_marks_report_actioned(self):
        response = self.run_action(self.report)

        self.assertEqual(response.status_code, 200)
        self.opportunity.refresh_from_db()
        self.report.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertEqual(self.opportunity.status, "closed")
        self.assertEqual(self.opportunity.close_reason, "moderation")
        self.assertEqual(self.pending.status, "expired")
        self.assertEqual(self.report.status, "actioned")
        self.assertEqual(self.report.reviewed_by, self.moderator)
        self.assertIsNotNone(self.report.reviewed_at)

    def test_skips_reports_without_an_open_opportunity(self):
        self.run_action(self.no_opportunity)

        self.no_opportunity.refresh_from_db()
        self.assertEqual(self.no_opportunity.status, "open")
