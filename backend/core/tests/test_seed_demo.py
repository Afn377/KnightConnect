from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import User
from analytics.pilot import pilot_metrics
from connections.models import ConnectionFeedback, ConnectionRequest
from core.testing import make_user
from matching.models import MatchResult
from opportunities.models import Opportunity
from safety.models import Block


def seed(**options):
    call_command("seed_demo", stdout=StringIO(), **options)


class SeedDemoTests(TestCase):
    def test_creates_a_full_demo_world(self):
        seed(students=40)

        demo = User.objects.filter(email__startswith="demo-")
        self.assertEqual(demo.count(), 40)
        self.assertTrue(all(u.email.endswith("@scarletmail.rutgers.edu") for u in demo))
        self.assertTrue(Opportunity.objects.filter(status="open").exists())
        self.assertTrue(Opportunity.objects.filter(status="draft").exists())
        self.assertTrue(Opportunity.objects.filter(status="expired").exists())
        self.assertTrue(ConnectionRequest.objects.filter(status="accepted").exists())
        self.assertTrue(ConnectionRequest.objects.filter(status="pending").exists())
        self.assertTrue(ConnectionFeedback.objects.exists())
        self.assertTrue(MatchResult.objects.exists())
        self.assertEqual(Block.objects.count(), 1)
        # Edge cases the frontend should handle.
        self.assertTrue(demo.filter(contact_methods__isnull=True).exists())
        self.assertTrue(demo.filter(open_to_requests=False).exists())

    def test_feeds_the_pilot_metrics(self):
        seed(students=40)

        pilot = pilot_metrics()

        self.assertGreater(pilot["qualified_matches"]["measured"], 0)
        self.assertIsNotNone(pilot["useful_connections"]["rate"])

    def test_same_seed_gives_the_same_data(self):
        seed(students=30, seed=7)
        first = sorted(User.objects.values_list("email", "display_name", "major"))
        first_posts = sorted(Opportunity.objects.values_list("title", "status", "team_capacity"))

        seed(students=30, seed=7, reset=True)

        self.assertEqual(sorted(User.objects.values_list("email", "display_name", "major")), first)
        self.assertEqual(sorted(Opportunity.objects.values_list("title", "status", "team_capacity")), first_posts)

    def test_refuses_to_run_twice_without_reset(self):
        seed(students=10)

        with self.assertRaisesMessage(CommandError, "--reset"):
            seed(students=10)

    def test_reset_leaves_real_data_alone(self):
        real = make_user("realstudent@rutgers.edu")
        seed(students=10, allow_real_data=True)

        seed(students=10, reset=True, allow_real_data=True)

        self.assertTrue(User.objects.filter(pk=real.pk).exists())
        self.assertEqual(User.objects.filter(email__startswith="demo-").count(), 10)

    def test_refuses_a_database_with_real_students(self):
        make_user("realstudent@rutgers.edu")

        with self.assertRaisesMessage(CommandError, "real student"):
            seed(students=10)
        self.assertFalse(User.objects.filter(email__startswith="demo-").exists())
