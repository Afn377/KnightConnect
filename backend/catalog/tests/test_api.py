from catalog.models import Interest, Role, Skill
from core.testing import APITestCase, make_user


class SkillListTests(APITestCase):
    url = "/api/skills/"

    def test_lists_all_skills_alphabetically(self):
        Skill.objects.create(name="React")
        Skill.objects.create(name="Python")
        self.login(make_user())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{"slug": "python", "name": "Python"}, {"slug": "react", "name": "React"}])

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)


class RoleListTests(APITestCase):
    url = "/api/roles/"

    def test_lists_all_roles_alphabetically(self):
        Role.objects.create(name="Frontend developer")
        Role.objects.create(name="Backend developer")
        self.login(make_user())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {"slug": "backend-developer", "name": "Backend developer"},
                {"slug": "frontend-developer", "name": "Frontend developer"},
            ],
        )

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)


class InterestListTests(APITestCase):
    url = "/api/interests/"

    def test_lists_all_interests_alphabetically(self):
        Interest.objects.create(name="Fintech")
        Interest.objects.create(name="Climate")
        self.login(make_user())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"slug": "climate", "name": "Climate"}, {"slug": "fintech", "name": "Fintech"}],
        )

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
