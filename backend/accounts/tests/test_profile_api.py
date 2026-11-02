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


class MeUpdateTests(APITestCase):
    url = "/api/me/"

    def setUp(self):
        super().setUp()
        self.backend = Role.objects.create(name="Backend developer")
        self.designer = Role.objects.create(name="Designer")
        self.fintech = Interest.objects.create(name="Fintech")
        self.python = Skill.objects.create(name="Python")
        self.react = Skill.objects.create(name="React")
        self.user = self.login(make_user("netid@rutgers.edu", preferred_roles=[self.designer]))
        UserSkill.objects.create(user=self.user, skill=self.react)

    def patch(self, data):
        return self.client.patch(self.url, data, format="json")

    def test_updates_profile_fields(self):
        response = self.patch(
            {
                "display_name": "Scarlet Knight",
                "bio": "Looking for a HackRU team",
                "open_to_requests": False,
                "availability": ["weekday_evening", "weekend_afternoon"],
                "commitment": "heavy",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Scarlet Knight")
        self.assertEqual(self.user.bio, "Looking for a HackRU team")
        self.assertFalse(self.user.open_to_requests)
        self.assertEqual(self.user.availability, ["weekday_evening", "weekend_afternoon"])
        self.assertEqual(self.user.commitment, "heavy")
        self.assertEqual(response.json()["display_name"], "Scarlet Knight")

    def test_replaces_roles_and_interests_by_slug(self):
        response = self.patch({"preferred_roles": ["backend-developer"], "interests": ["fintech"]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.user.preferred_roles.all()), [self.backend])
        self.assertEqual(list(self.user.interests.all()), [self.fintech])

    def test_replaces_skills(self):
        response = self.patch({"skills": [{"skill": "python", "proficiency": "beginner"}]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(self.user.user_skills.values_list("skill__slug", "proficiency")),
            [("python", "beginner")],
        )
        self.assertEqual(response.json()["skills"], [{"skill": {"slug": "python", "name": "Python"}, "proficiency": "beginner"}])

    def test_leaves_omitted_fields_untouched(self):
        self.patch({"bio": "Updated"})

        self.assertEqual(list(self.user.preferred_roles.all()), [self.designer])
        self.assertEqual(self.user.user_skills.count(), 1)

    def test_rejects_unknown_slug(self):
        response = self.patch({"preferred_roles": ["astronaut"]})

        self.assertEqual(response.status_code, 400)
        self.assertIn("preferred_roles", response.json())

    def test_rejects_duplicate_skills(self):
        response = self.patch(
            {"skills": [{"skill": "python", "proficiency": "beginner"}, {"skill": "python", "proficiency": "advanced"}]}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.user.user_skills.get().skill, self.react)

    def test_rejects_invalid_availability(self):
        response = self.patch({"availability": ["whenever"]})

        self.assertEqual(response.status_code, 400)
        self.assertIn("availability", response.json())

    def test_email_cannot_be_changed(self):
        self.patch({"email": "other@rutgers.edu"})

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "netid@rutgers.edu")

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.patch({"bio": "x"}).status_code, 401)
