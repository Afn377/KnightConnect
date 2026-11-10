from datetime import datetime, timezone
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from catalog.models import Event, Interest, Role, Skill
from catalog.seed_data import INTERESTS, ROLES, SKILLS


class SeedCatalogTests(TestCase):
    def seed(self, *args):
        out = StringIO()
        call_command("seed_catalog", *args, stdout=out)
        return out.getvalue()

    def test_loads_starter_skills_roles_and_interests(self):
        self.seed()

        self.assertEqual(Skill.objects.count(), len(SKILLS))
        self.assertEqual(Role.objects.count(), len(ROLES))
        self.assertEqual(Interest.objects.count(), len(INTERESTS))
        self.assertTrue(Skill.objects.filter(name="Python").exists())
        self.assertTrue(Role.objects.filter(name="Backend developer").exists())

    def test_running_twice_creates_no_duplicates(self):
        self.seed()
        output = self.seed()

        self.assertEqual(Skill.objects.count(), len(SKILLS))
        self.assertEqual(Role.objects.count(), len(ROLES))
        self.assertEqual(Interest.objects.count(), len(INTERESTS))
        self.assertIn("0 skills", output)

    def test_keeps_existing_entries(self):
        Skill.objects.create(name="python", slug="python")
        Skill.objects.create(name="Rust")

        self.seed()

        self.assertEqual(Skill.objects.filter(slug="python").count(), 1)
        self.assertTrue(Skill.objects.filter(name="Rust").exists())

    def test_creates_or_updates_an_event_from_options(self):
        args = [
            "--event", "HackRU Spring 2027",
            "--starts", "2027-04-10T10:00:00-04:00",
            "--ends", "2027-04-11T14:00:00-04:00",
            "--recruiting-ends", "2027-04-10T09:00:00-04:00",
        ]
        self.seed(*args)
        self.seed(*args[:-2])

        event = Event.objects.get()
        self.assertEqual(event.slug, "hackru-spring-2027")
        self.assertEqual(event.starts_at, datetime(2027, 4, 10, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(event.ends_at, datetime(2027, 4, 11, 18, 0, tzinfo=timezone.utc))
        # Without --recruiting-ends, recruiting closes when the event starts.
        self.assertEqual(event.recruiting_ends_at, event.starts_at)

    def test_event_requires_dates(self):
        with self.assertRaises(CommandError):
            self.seed("--event", "HackRU Spring 2027")
