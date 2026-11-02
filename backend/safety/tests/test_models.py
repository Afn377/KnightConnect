from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User

from ..models import Block, Report


class BlockTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice@rutgers.edu")
        self.bob = User.objects.create_user("bob@rutgers.edu")
        self.carol = User.objects.create_user("carol@rutgers.edu")

    def test_between_matches_either_direction(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)

        self.assertTrue(Block.objects.between(self.alice, self.bob).exists())
        self.assertTrue(Block.objects.between(self.bob, self.alice).exists())
        self.assertFalse(Block.objects.between(self.alice, self.carol).exists())

    def test_cannot_block_self(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Block.objects.create(blocker=self.alice, blocked=self.alice)

    def test_block_is_unique_per_pair(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Block.objects.create(blocker=self.alice, blocked=self.bob)


class ReportTests(TestCase):
    def test_report_survives_reporter_account_deletion(self):
        reporter = User.objects.create_user("reporter@rutgers.edu")
        reported = User.objects.create_user("reported@rutgers.edu")
        report = Report.objects.create(reporter=reporter, reported_user=reported, reason=Report.Reason.SPAM)

        reporter.delete()
        report.refresh_from_db()

        self.assertIsNone(report.reporter)
        self.assertEqual(report.status, Report.Status.OPEN)
