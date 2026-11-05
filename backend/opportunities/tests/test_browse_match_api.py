from accounts.models import UserSkill
from catalog.models import Interest, Role, Skill
from core.testing import APITestCase, make_opportunity, make_user
from opportunities.models import OpportunityRole, OpportunitySkill


class BrowseMatchTests(APITestCase):
    url = "/api/opportunities/"

    def setUp(self):
        super().setUp()
        self.python = Skill.objects.create(name="Python")
        self.backend = Role.objects.create(name="Backend developer")
        self.ai = Interest.objects.create(name="AI")
        self.viewer = self.login(
            make_user(availability=["weekend_morning"], commitment="full", preferred_roles=[self.backend], interests=[self.ai])
        )
        UserSkill.objects.create(user=self.viewer, skill=self.python)

    def post(self, title, good_fit):
        opportunity = make_opportunity(title=title, interests=[self.ai] if good_fit else [])
        OpportunityRole.objects.create(
            opportunity=opportunity, role=self.backend if good_fit else Role.objects.get_or_create(name="Designer")[0]
        )
        if good_fit:
            OpportunitySkill.objects.create(opportunity=opportunity, skill=self.python)
        return opportunity

    def results(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return response.json()["results"]

    def test_each_card_explains_why_it_matches(self):
        self.post("Good fit", good_fit=True)

        match = self.results()[0]["match"]

        self.assertGreater(match["score"], 0)
        self.assertTrue(match["meets_requirements"])
        labels = [factor["label"] for factor in match["explanations"]]
        self.assertIn("Python experience", labels)
        self.assertIn("Fits the Backend developer role", labels)
        self.assertIn("Interested in AI", labels)

    def test_flags_posts_whose_requirements_are_not_met(self):
        opportunity = self.post("Needs Rust", good_fit=False)
        OpportunitySkill.objects.create(opportunity=opportunity, skill=Skill.objects.create(name="Rust"), requirement_type="required")

        self.assertFalse(self.results()[0]["match"]["meets_requirements"])

    def test_own_posts_have_no_match(self):
        make_opportunity(owner=self.viewer)

        self.assertIsNone(self.results()[0]["match"])

    def test_sorts_by_best_match_by_default(self):
        self.post("Good fit", good_fit=True)
        self.post("Newer but weaker", good_fit=False)

        self.assertEqual([item["title"] for item in self.results()], ["Good fit", "Newer but weaker"])
        self.assertEqual([item["title"] for item in self.results(sort="best_match")], ["Good fit", "Newer but weaker"])

    def test_best_match_sort_pages_correctly(self):
        for index in range(25):
            self.post(f"Weak {index}", good_fit=False)
        self.post("Good fit", good_fit=True)

        first_page = self.client.get(self.url).json()

        self.assertEqual(first_page["count"], 26)
        self.assertEqual(len(first_page["results"]), 20)
        self.assertEqual(first_page["results"][0]["title"], "Good fit")
        self.assertEqual(len(self.client.get(self.url, {"page": 2}).json()["results"]), 6)

    def test_rejects_unknown_sort(self):
        self.assertEqual(self.client.get(self.url, {"sort": "random"}).status_code, 400)
