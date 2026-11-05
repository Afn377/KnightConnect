from catalog.models import Role
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from opportunities.models import OpportunityRole


class TeamRosterTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user(display_name="Alex Chen", major="Computer Science", year="senior")
        self.opportunity = make_opportunity(owner=self.owner)
        role = OpportunityRole.objects.create(opportunity=self.opportunity, role=Role.objects.create(name="Designer"))
        self.member = make_user(display_name="Maya Patel", major="Computer Science", year="junior")
        ConnectionRequest.objects.create(
            opportunity=self.opportunity, opportunity_role=role, kind="join",
            sender=self.member, recipient=self.owner, status="accepted",
        )
        ConnectionRequest.objects.create(opportunity=self.opportunity, kind="join", sender=make_user(), recipient=self.owner)

    def get(self):
        return self.client.get(f"/api/opportunities/{self.opportunity.id}/team/")

    def test_owner_sees_confirmed_team(self):
        self.login(self.owner)

        response = self.get()

        self.assertEqual(response.status_code, 200)
        team = response.json()
        self.assertEqual([member["display_name"] for member in team], ["Alex Chen", "Maya Patel"])
        self.assertEqual(team[0]["is_owner"], True)
        self.assertEqual(team[1]["is_owner"], False)
        self.assertEqual(team[1]["year"], "junior")
        self.assertEqual(team[1]["role"], {"slug": "designer", "name": "Designer"})
        self.assertIsNone(team[0]["role"])

    def test_members_can_see_their_team(self):
        self.login(self.member)

        self.assertEqual(self.get().status_code, 200)

    def test_others_are_forbidden(self):
        self.login(make_user())

        self.assertEqual(self.get().status_code, 403)
