from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from catalog.models import Skill

from ..models import ContactMethod, User, UserSkill


class UserManagerTests(TestCase):
    def test_creates_user_with_normalized_email_and_no_password(self):
        user = User.objects.create_user("  NetID@Rutgers.EDU ")

        self.assertEqual(user.email, "netid@rutgers.edu")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.open_to_requests)

    def test_accepts_scarletmail(self):
        user = User.objects.create_user("netid@scarletmail.rutgers.edu")

        self.assertEqual(user.email, "netid@scarletmail.rutgers.edu")

    def test_rejects_non_rutgers_email(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user("someone@gmail.com")

    def test_rejects_lookalike_domain(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user("someone@notrutgers.edu")

    @override_settings(ALLOWED_EMAIL_DOMAINS=["example.edu"])
    def test_allowed_domains_are_configurable(self):
        User.objects.create_user("someone@example.edu")
        with self.assertRaises(ValidationError):
            User.objects.create_user("someone@rutgers.edu")

    def test_email_is_unique_case_insensitively(self):
        User.objects.create_user("netid@rutgers.edu")

        with self.assertRaises(ValidationError):
            User.objects.create_user("NETID@rutgers.edu")

    def test_superuser_has_password_and_staff_flags(self):
        admin = User.objects.create_superuser("admin@rutgers.edu", "a-strong-password-123")

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("a-strong-password-123"))


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("netid@rutgers.edu")

    def test_invalid_availability_fails_validation(self):
        self.user.availability = ["whenever"]

        with self.assertRaises(ValidationError):
            self.user.full_clean(exclude=["password"])

    def test_profile_complete_requires_core_fields(self):
        self.assertFalse(self.user.is_profile_complete)

        self.user.display_name = "Scarlet Knight"
        self.user.availability = ["weekend_afternoon"]
        self.user.commitment = "partial"

        self.assertTrue(self.user.is_profile_complete)

    def test_skill_can_only_be_added_once(self):
        skill = Skill.objects.create(name="Python")
        UserSkill.objects.create(user=self.user, skill=skill)

        with self.assertRaises(IntegrityError), transaction.atomic():
            UserSkill.objects.create(user=self.user, skill=skill, proficiency="advanced")

    def test_only_one_preferred_contact_method(self):
        ContactMethod.objects.create(user=self.user, kind="discord", value="knight#1", is_preferred=True)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ContactMethod.objects.create(user=self.user, kind="email", value="netid@rutgers.edu", is_preferred=True)
