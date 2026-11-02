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


class OpportunityCreateTests(OpportunityFixtures, APITestCase):
    url = "/api/opportunities/"

    def setUp(self):
        super().setUp()
        self.make_catalog()
        self.owner = self.login(make_user())
        self.event = make_event(name="HackRU Fall")

    def payload(self, **overrides):
        data = {
            "title": "HackRU Teammates Needed",
            "description": "Building an AI study buddy.",
            "opportunity_type": "hackathon",
            "event": "hackru-fall",
            "availability": ["weekend_morning", "weekend_afternoon"],
            "commitment": "full_event",
            "interests": ["ai"],
            "roles": [{"role": "backend-developer", "slots": 2, "notes": "Django or FastAPI"}, {"role": "designer"}],
            "skills": [
                {"skill": "python", "requirement_type": "required"},
                {"skill": "figma", "requirement_type": "preferred"},
            ],
            "expires_at": (timezone.now() + timedelta(days=3)).isoformat(),
        }
        data.update(overrides)
        return data

    def post(self, **overrides):
        return self.client.post(self.url, self.payload(**overrides), format="json")

    def test_creates_opportunity_owned_by_requester(self):
        response = self.post()

        self.assertEqual(response.status_code, 201, response.json())
        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.owner, self.owner)
        self.assertEqual(opportunity.event, self.event)
        self.assertEqual(opportunity.status, "open")
        self.assertEqual(list(opportunity.interests.values_list("slug", flat=True)), ["ai"])
        self.assertEqual(
            sorted(opportunity.roles.values_list("role__slug", "slots", "notes")),
            [("backend-developer", 2, "Django or FastAPI"), ("designer", 1, "")],
        )
        self.assertEqual(
            sorted(opportunity.opportunity_skills.values_list("skill__slug", "requirement_type")),
            [("figma", "preferred"), ("python", "required")],
        )
        body = response.json()
        self.assertEqual(body["id"], str(opportunity.id))
        self.assertTrue(body["is_owner"])
        self.assertEqual(len(body["roles"]), 2)
        self.assertEqual(body["roles"][0]["filled"], 0)

    def test_records_funnel_event(self):
        from analytics.models import FunnelEvent

        self.post()

        event = FunnelEvent.objects.get()
        self.assertEqual(event.event_type, "opportunity_created")
        self.assertEqual(event.user, self.owner)
        self.assertEqual(event.opportunity, Opportunity.objects.get())

    def test_event_is_optional(self):
        response = self.post(event=None, opportunity_type="personal_project")

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Opportunity.objects.get().event)

    def test_requires_at_least_one_role(self):
        self.assertEqual(self.post(roles=[]).status_code, 400)

    def test_rejects_duplicate_roles(self):
        response = self.post(roles=[{"role": "designer"}, {"role": "designer", "slots": 2}])

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Opportunity.objects.exists())

    def test_rejects_duplicate_skills(self):
        response = self.post(skills=[{"skill": "python"}, {"skill": "python", "requirement_type": "required"}])

        self.assertEqual(response.status_code, 400)

    def test_rejects_unknown_slugs(self):
        self.assertEqual(self.post(roles=[{"role": "astronaut"}]).status_code, 400)
        self.assertEqual(self.post(event="no-such-event").status_code, 400)

    def test_rejects_past_or_distant_expiry(self):
        self.assertEqual(self.post(expires_at=(timezone.now() - timedelta(hours=1)).isoformat()).status_code, 400)
        self.assertEqual(self.post(event=None, expires_at=(timezone.now() + timedelta(days=45)).isoformat()).status_code, 400)

    def test_rejects_expiry_after_event_recruiting_deadline(self):
        response = self.post(expires_at=(self.event.recruiting_ends_at + timedelta(hours=1)).isoformat())

        self.assertEqual(response.status_code, 400)
        self.assertIn("expires_at", response.json())

    def test_rejects_event_no_longer_recruiting(self):
        now = timezone.now()
        make_event(name="Started", starts_at=now - timedelta(hours=1), ends_at=now + timedelta(days=1), recruiting_ends_at=now - timedelta(hours=1))

        response = self.post(event="started", expires_at=(now + timedelta(hours=5)).isoformat())

        self.assertEqual(response.status_code, 400)
        self.assertIn("event", response.json())

    def test_rejects_invalid_availability(self):
        self.assertEqual(self.post(availability=["sometime"]).status_code, 400)

    def test_rejects_invalid_slot_count(self):
        self.assertEqual(self.post(roles=[{"role": "designer", "slots": 0}]).status_code, 400)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.post().status_code, 401)
