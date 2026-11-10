from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from ..models import Event, Skill


class SkillTests(TestCase):
    def test_slug_is_generated_from_name(self):
        skill = Skill.objects.create(name="Machine Learning")

        self.assertEqual(skill.slug, "machine-learning")

    def test_names_are_unique_case_insensitively(self):
        Skill.objects.create(name="React")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Skill.objects.create(name="react", slug="react-2")


class EventTests(TestCase):
    def make_event(self, **overrides):
        now = timezone.now()
        fields = {
            "name": "HackRU Fall 2026",
            "starts_at": now + timedelta(days=7),
            "ends_at": now + timedelta(days=8),
            "recruiting_ends_at": now + timedelta(days=7),
        }
        fields.update(overrides)
        return Event.objects.create(**fields)

    def test_is_recruiting_until_deadline(self):
        self.assertTrue(self.make_event().is_recruiting)
        self.assertFalse(
            self.make_event(
                name="Past",
                recruiting_ends_at=timezone.now() - timedelta(minutes=1),
            ).is_recruiting
        )

    def test_end_must_not_precede_start(self):
        now = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_event(starts_at=now, ends_at=now - timedelta(hours=1), recruiting_ends_at=now - timedelta(hours=2))
