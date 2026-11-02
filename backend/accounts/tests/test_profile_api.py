from accounts.models import UserSkill
from catalog.models import Interest, Role, Skill
from core.testing import APITestCase, make_user


class MeRetrieveTests(APITestCase):
    url = "/api/me/"

    def setUp(self):
        super().setUp()
        self.backend = Role.objects.create(name="Backend developer")
        self.ai = Interest.objects.create(name="AI/ML")
        self.python = Skill.objects.create(name="Python")
        self.user = make_user(
            "netid@rutgers.edu",
            display_name="Scarlet Knight",
            bio="CS junior",
            availability=["weekend_morning"],
            commitment="moderate",
            preferred_roles=[self.backend],
            interests=[self.ai],
        )
        UserSkill.objects.create(user=self.user, skill=self.python, proficiency="advanced")

    def test_returns_own_profile(self):
        self.login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], str(self.user.id))
        self.assertEqual(body["email"], "netid@rutgers.edu")
        self.assertEqual(body["display_name"], "Scarlet Knight")
        self.assertEqual(body["bio"], "CS junior")
        self.assertTrue(body["open_to_requests"])
        self.assertEqual(body["availability"], ["weekend_morning"])
        self.assertEqual(body["commitment"], "moderate")
        self.assertEqual(body["preferred_roles"], [{"slug": "backend-developer", "name": "Backend developer"}])
        self.assertEqual(body["interests"], [{"slug": "aiml", "name": "AI/ML"}])
        self.assertEqual(body["skills"], [{"skill": {"slug": "python", "name": "Python"}, "proficiency": "advanced"}])
        self.assertTrue(body["is_profile_complete"])

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
