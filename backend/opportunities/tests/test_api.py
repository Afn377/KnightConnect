from datetime import timedelta

from django.utils import timezone

from catalog.models import Interest, Role, Skill
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_event, make_opportunity, make_user
from opportunities.models import Opportunity, OpportunityRole, OpportunitySkill
from safety.models import Block


class OpportunityFixtures:
    def make_catalog(self):
        self.backend = Role.objects.create(name="Backend developer")
        self.designer = Role.objects.create(name="Designer")
        self.python = Skill.objects.create(name="Python")
        self.figma = Skill.objects.create(name="Figma")
        self.ai = Interest.objects.create(name="AI")


class OpportunityBrowseTests(OpportunityFixtures, APITestCase):
    url = "/api/opportunities/"

    def setUp(self):
        super().setUp()
        self.make_catalog()
        self.viewer = self.login(make_user())

    def browse(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def titles(self, **params):
        return {item["title"] for item in self.browse(**params)["results"]}

    def test_lists_active_opportunities_with_details(self):
        event = make_event(name="HackRU Fall")
        owner = make_user(display_name="Jane Doe")
        opportunity = make_opportunity(owner=owner, event=event, interests=[self.ai])
        role = OpportunityRole.objects.create(opportunity=opportunity, role=self.backend, slots=2, notes="Django")
        OpportunitySkill.objects.create(opportunity=opportunity, skill=self.python, requirement_type="required")
        ConnectionRequest.objects.create(
            opportunity=opportunity, opportunity_role=role, kind="join", sender=make_user(), recipient=owner, status="accepted"
        )

        body = self.browse()

        self.assertEqual(body["count"], 1)
        item = body["results"][0]
        self.assertEqual(item["id"], str(opportunity.id))
        self.assertEqual(item["title"], opportunity.title)
        self.assertEqual(item["description"], opportunity.description)
        self.assertEqual(item["opportunity_type"], "hackathon")
        self.assertEqual(item["event"], {"slug": "hackru-fall", "name": "HackRU Fall"})
        self.assertEqual(item["owner"], {"id": str(owner.id), "display_name": "Jane Doe"})
        self.assertEqual(item["availability"], opportunity.availability)
        self.assertEqual(item["commitment"], "full_event")
        self.assertEqual(item["interests"], [{"slug": "ai", "name": "AI"}])
        self.assertEqual(
            item["roles"],
            [{"role": {"slug": "backend-developer", "name": "Backend developer"}, "slots": 2, "filled": 1, "notes": "Django"}],
        )
        self.assertEqual(item["skills"], [{"skill": {"slug": "python", "name": "Python"}, "requirement_type": "required"}])
        self.assertEqual(item["status"], "open")
        self.assertFalse(item["is_owner"])
        self.assertIn("expires_at", item)
        self.assertIn("created_at", item)

    def test_excludes_inactive_and_hidden_opportunities(self):
        make_opportunity(title="Visible")
        make_opportunity(title="Closed").close(Opportunity.CloseReason.OWNER_CLOSED)
        make_opportunity(title="Past expiry", expires_at=timezone.now() - timedelta(minutes=1))
        make_opportunity(title="Owner deleting", owner=make_user(deletion_scheduled_for=timezone.now() + timedelta(days=1)))
        make_opportunity(title="Owner disabled", owner=make_user(is_active=False))
        blocked = make_opportunity(title="Blocked by viewer")
        Block.objects.create(blocker=self.viewer, blocked=blocked.owner)
        blocker = make_opportunity(title="Owner blocked viewer")
        Block.objects.create(blocker=blocker.owner, blocked=self.viewer)

        self.assertEqual(self.titles(), {"Visible"})

    def test_newest_first(self):
        make_opportunity(title="Older")
        make_opportunity(title="Newer")

        self.assertEqual([item["title"] for item in self.browse()["results"]], ["Newer", "Older"])

    def test_filters_by_event(self):
        event = make_event(name="HackRU Fall")
        make_opportunity(title="At HackRU", event=event)
        make_opportunity(title="Personal", opportunity_type="personal_project")

        self.assertEqual(self.titles(event="hackru-fall"), {"At HackRU"})

    def test_filters_by_role(self):
        wants_backend = make_opportunity(title="Needs backend")
        OpportunityRole.objects.create(opportunity=wants_backend, role=self.backend)
        wants_designer = make_opportunity(title="Needs designer")
        OpportunityRole.objects.create(opportunity=wants_designer, role=self.designer)

        self.assertEqual(self.titles(role="designer"), {"Needs designer"})

    def test_filters_by_skill(self):
        python = make_opportunity(title="Python project")
        OpportunitySkill.objects.create(opportunity=python, skill=self.python)
        make_opportunity(title="Other")

        self.assertEqual(self.titles(skill="python"), {"Python project"})

    def test_filters_by_type(self):
        make_opportunity(title="Hackathon")
        make_opportunity(title="Research", opportunity_type="research")

        self.assertEqual(self.titles(type="research"), {"Research"})

    def test_search_matches_title_description_role_and_skill(self):
        make_opportunity(title="Climate dashboard")
        make_opportunity(title="Second", description="We are building a climate model")
        by_role = make_opportunity(title="Third")
        OpportunityRole.objects.create(opportunity=by_role, role=self.designer)
        by_skill = make_opportunity(title="Fourth")
        OpportunitySkill.objects.create(opportunity=by_skill, skill=self.figma)
        make_opportunity(title="Unrelated")

        self.assertEqual(self.titles(q="climate"), {"Climate dashboard", "Second"})
        self.assertEqual(self.titles(q="design"), {"Third"})
        self.assertEqual(self.titles(q="figma"), {"Fourth"})

    def test_matching_several_roles_returns_opportunity_once(self):
        opportunity = make_opportunity(title="Both")
        OpportunityRole.objects.create(opportunity=opportunity, role=self.backend)
        OpportunityRole.objects.create(opportunity=opportunity, role=self.designer)

        self.assertEqual(self.browse(q="e")["count"], 1)

    def test_own_opportunities_are_marked(self):
        make_opportunity(owner=self.viewer)

        self.assertTrue(self.browse()["results"][0]["is_owner"])

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 401)
