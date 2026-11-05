from accounts.models import UserSkill
from analytics.models import FunnelEvent
from catalog.models import Role, Skill
from core.testing import APITestCase, make_opportunity, make_user
from matching.models import MatchResult
from opportunities.models import Opportunity, OpportunityRole, OpportunitySkill


class MatchingApiFixtures:
    def make_world(self):
        self.python = Skill.objects.create(name="Python")
        self.backend = Role.objects.create(name="Backend developer")
        self.owner = make_user(display_name="Owner")
        self.opportunity = make_opportunity(owner=self.owner, availability=["weekend_morning"], commitment="full_event")
        OpportunityRole.objects.create(opportunity=self.opportunity, role=self.backend)
        OpportunitySkill.objects.create(opportunity=self.opportunity, skill=self.python, requirement_type="required")

    def make_candidate(self, **fields):
        defaults = {"availability": ["weekend_morning"], "commitment": "full_event"}
        defaults.update(fields)
        candidate = make_user(**defaults)
        UserSkill.objects.create(user=candidate, skill=self.python)
        return candidate


class OpportunityMatchesTests(MatchingApiFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.make_world()

    def get(self):
        return self.client.get(f"/api/opportunities/{self.opportunity.id}/matches/")

    def test_owner_gets_ranked_candidates_with_explanations(self):
        strong = self.make_candidate(display_name="Strong", preferred_roles=[self.backend])
        weak = self.make_candidate(display_name="Weak")
        self.login(self.owner)

        response = self.get()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        results = body["results"]
        self.assertEqual([item["candidate"]["id"] for item in results], [str(strong.id), str(weak.id)])
        self.assertEqual([item["rank"] for item in results], [1, 2])
        self.assertEqual(results[0]["candidate"]["display_name"], "Strong")
        self.assertNotIn("email", results[0]["candidate"])
        self.assertIn("Fits the Backend developer role", [factor["label"] for factor in results[0]["explanations"]])
        self.assertIsInstance(results[0]["score"], float)
        self.assertTrue(body["sparse"])

    def test_persists_results_and_records_them_as_shown(self):
        candidate = self.make_candidate()
        self.login(self.owner)

        body = self.get().json()

        result = MatchResult.objects.get()
        self.assertEqual(str(result.batch_id), body["batch_id"])
        self.assertEqual(body["results"][0]["match_id"], str(result.id))
        self.assertEqual(result.direction, "candidates")
        self.assertEqual(result.candidate, candidate)
        self.assertEqual(result.rank, 1)
        event = FunnelEvent.objects.get(event_type="recommendation_shown")
        self.assertEqual(event.user, self.owner)
        self.assertEqual(event.match_result, result)

    def test_not_sparse_with_three_or_more_matches(self):
        for _ in range(3):
            self.make_candidate()
        self.login(self.owner)

        self.assertFalse(self.get().json()["sparse"])

    def test_empty_results_are_sparse(self):
        self.login(self.owner)

        body = self.get().json()

        self.assertEqual(body["results"], [])
        self.assertTrue(body["sparse"])

    def test_non_owner_is_forbidden(self):
        self.login(make_user())

        self.assertEqual(self.get().status_code, 403)

    def test_closed_opportunity_is_conflict(self):
        self.opportunity.close(Opportunity.CloseReason.FILLED)
        self.login(self.owner)

        self.assertEqual(self.get().status_code, 409)

    def test_requires_authentication(self):
        self.assertEqual(self.get().status_code, 401)


class RecommendationsTests(MatchingApiFixtures, APITestCase):
    url = "/api/recommendations/"

    def setUp(self):
        super().setUp()
        self.make_world()
        self.student = self.login(self.make_candidate(preferred_roles=[self.backend]))

    def test_returns_ranked_opportunities_with_explanations(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        result = body["results"][0]
        self.assertEqual(result["rank"], 1)
        self.assertEqual(result["opportunity"]["id"], str(self.opportunity.id))
        self.assertEqual(result["opportunity"]["roles"][0]["role"]["slug"], "backend-developer")
        self.assertIn("Fits the Backend developer role", [factor["label"] for factor in result["explanations"]])
        self.assertTrue(body["sparse"])

    def test_persists_results_and_records_them_as_shown(self):
        body = self.client.get(self.url).json()

        result = MatchResult.objects.get()
        self.assertEqual(result.direction, "opportunities")
        self.assertEqual(result.candidate, self.student)
        self.assertEqual(str(result.batch_id), body["batch_id"])
        self.assertTrue(FunnelEvent.objects.filter(event_type="recommendation_shown", user=self.student, match_result=result).exists())

    def test_empty_when_nothing_fits(self):
        self.opportunity.close(Opportunity.CloseReason.OWNER_CLOSED)

        body = self.client.get(self.url).json()

        self.assertEqual(body["results"], [])
        self.assertTrue(body["sparse"])

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 401)
