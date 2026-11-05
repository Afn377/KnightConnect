import uuid
from datetime import timedelta

from django.utils import timezone

from accounts.models import ContactMethod, UserSkill
from catalog.models import Role, Skill
from core.testing import APITestCase, make_user
from safety.models import Block


class PublicProfileTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.viewer = self.login(make_user())
        self.student = make_user(
            "student@rutgers.edu",
            display_name="Jane Doe",
            bio="Designer",
            availability=["weekend_evening"],
            commitment="partial",
            preferred_roles=[Role.objects.create(name="Designer")],
        )
        UserSkill.objects.create(user=self.student, skill=Skill.objects.create(name="Figma"), proficiency="advanced")
        ContactMethod.objects.create(user=self.student, kind="discord", value="jane")

    def get(self, user_id):
        return self.client.get(f"/api/users/{user_id}/")

    def test_returns_public_profile_without_private_details(self):
        response = self.get(self.student.id)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], str(self.student.id))
        self.assertEqual(body["display_name"], "Jane Doe")
        self.assertEqual(body["bio"], "Designer")
        self.assertEqual(body["availability"], ["weekend_evening"])
        self.assertEqual(body["commitment"], "partial")
        self.assertEqual(body["preferred_roles"], [{"slug": "designer", "name": "Designer"}])
        self.assertEqual(body["skills"], [{"skill": {"slug": "figma", "name": "Figma"}, "proficiency": "advanced"}])
        self.assertNotIn("email", body)
        self.assertNotIn("contact_methods", body)
        self.assertNotIn("jane", str(body).replace("Jane Doe", ""))

    def test_hidden_when_viewer_blocked_student(self):
        Block.objects.create(blocker=self.viewer, blocked=self.student)

        self.assertEqual(self.get(self.student.id).status_code, 404)

    def test_hidden_when_student_blocked_viewer(self):
        Block.objects.create(blocker=self.student, blocked=self.viewer)

        self.assertEqual(self.get(self.student.id).status_code, 404)

    def test_hidden_when_account_pending_deletion(self):
        self.student.deletion_scheduled_for = timezone.now() + timedelta(days=3)
        self.student.save()

        self.assertEqual(self.get(self.student.id).status_code, 404)

    def test_hidden_when_account_disabled(self):
        self.student.is_active = False
        self.student.save()

        self.assertEqual(self.get(self.student.id).status_code, 404)

    def test_unknown_user_is_404(self):
        self.assertEqual(self.get(uuid.uuid4()).status_code, 404)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.get(self.student.id).status_code, 401)
