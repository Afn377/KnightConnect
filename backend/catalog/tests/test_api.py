from catalog.models import Skill
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
