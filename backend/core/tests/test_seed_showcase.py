"""The showcase story must hold exactly as the demo script describes it."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User
from core.management.commands.seed_showcase import JOINER_EMAIL, OWNER_EMAIL, STAR_POST
from core.testing import APITestCase, make_user
from opportunities.models import Opportunity


def seed(**options):
    out = StringIO()
    call_command("seed_showcase", stdout=out, **options)
    return out.getvalue()


class SeedShowcaseTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.output = seed()
        self.owner = User.objects.get(email=OWNER_EMAIL)
        self.joiner = User.objects.get(email=JOINER_EMAIL)
        self.star = Opportunity.objects.get(title=STAR_POST, owner=self.owner)

    def test_prints_presenter_accounts(self):
        self.assertIn(OWNER_EMAIL, self.output)
        self.assertIn(JOINER_EMAIL, self.output)

    def test_joiner_is_the_top_match_with_explanations(self):
        self.login(self.owner)
        response = self.client.get(f"/api/opportunities/{self.star.id}/matches/").json()

        self.assertFalse(response["sparse"])
        self.assertGreaterEqual(len(response["results"]), 5)
        top = response["results"][0]
        self.assertEqual(top["candidate"]["display_name"], "Jordan T.")
        self.assertGreaterEqual(len(top["explanations"]), 3)

    def test_star_post_is_the_joiners_top_recommendation(self):
        self.login(self.joiner)
        results = self.client.get("/api/recommendations/").json()["results"]

        self.assertEqual(results[0]["opportunity"]["title"], STAR_POST)
        self.assertGreaterEqual(len(results), 3)

    def test_browse_shows_a_full_campus(self):
        self.login(self.joiner)
        results = self.client.get("/api/opportunities/").json()["results"]

        self.assertGreaterEqual(len(results), 7)

    def test_requests_page_has_existing_activity(self):
        self.login(self.owner)
        incoming = self.client.get("/api/requests/", {"box": "incoming"}).json()["results"]
        self.assertEqual(sorted(r["status"] for r in incoming), ["accepted", "pending"])

        self.login(self.joiner)
        outgoing = self.client.get("/api/requests/", {"box": "outgoing"}).json()["results"]
        self.assertEqual([r["status"] for r in outgoing], ["pending"])

    def test_live_demo_request_accept_reveals_contacts(self):
        self.login(self.joiner)
        sent = self.client.post(
            "/api/requests/",
            {"opportunity": str(self.star.id), "role": "backend-developer", "message": "I know Django."},
            format="json",
        )
        self.assertEqual(sent.status_code, 201, sent.content)

        self.login(self.owner)
        accepted = self.client.post(f"/api/requests/{sent.json()['id']}/accept/")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual(accepted.json()["contact_methods"], [{"kind": "discord", "value": "jordan.builds"}])

        self.login(self.joiner)
        detail = self.client.get(f"/api/requests/{sent.json()['id']}/").json()
        self.assertEqual(detail["contact_methods"], [{"kind": "discord", "value": "priya.designs"}])

    def test_reset_restores_the_same_starting_state(self):
        self.login(self.joiner)
        self.client.post("/api/requests/", {"opportunity": str(self.star.id)}, format="json")
        before = sorted(User.objects.values_list("email", flat=True))

        seed(reset=True)

        self.assertEqual(sorted(User.objects.values_list("email", flat=True)), before)
        star = Opportunity.objects.get(title=STAR_POST)
        self.assertFalse(star.connection_requests.filter(sender__email=JOINER_EMAIL).exists())

    def test_refuses_to_run_twice_without_reset(self):
        with self.assertRaisesMessage(CommandError, "--reset"):
            seed()

    def test_refuses_a_database_with_real_students(self):
        make_user("realstudent@rutgers.edu")

        with self.assertRaisesMessage(CommandError, "real student"):
            seed(reset=True)
