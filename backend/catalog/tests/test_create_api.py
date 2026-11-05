from catalog.models import Skill
from core.testing import APITestCase, make_user, throttle_rates


class SkillCreateTests(APITestCase):
    url = "/api/skills/"

    def setUp(self):
        super().setUp()
        self.login(make_user())

    def post(self, name):
        return self.client.post(self.url, {"name": name}, format="json")

    def test_adds_a_new_skill(self):
        response = self.post("  Svelte ")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"slug": "svelte", "name": "Svelte"})
        self.assertTrue(Skill.objects.filter(name="Svelte").exists())

    def test_returns_existing_skill_instead_of_duplicating(self):
        Skill.objects.create(name="React")

        response = self.post("react")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"slug": "react", "name": "React"})
        self.assertEqual(Skill.objects.count(), 1)

    def test_gives_colliding_names_a_unique_slug(self):
        Skill.objects.create(name="C")

        response = self.post("C++")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"slug": "c-2", "name": "C++"})

    def test_rejects_blank_too_long_or_unsluggable_names(self):
        self.assertEqual(self.post("   ").status_code, 400)
        self.assertEqual(self.post("x" * 65).status_code, 400)
        self.assertEqual(self.post("+++").status_code, 400)

    @throttle_rates(catalog_create="2/day")
    def test_rate_limited(self):
        self.post("One")
        self.post("Two")

        self.assertEqual(self.post("Three").status_code, 429)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.post("Svelte").status_code, 401)
