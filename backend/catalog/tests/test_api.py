from datetime import timedelta

from django.utils import timezone

from catalog.models import Interest, Role, Skill
from core.testing import APITestCase, make_event, make_user


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


class EventListTests(APITestCase):
    url = "/api/events/"

    def test_lists_active_upcoming_events_by_start_time(self):
        now = timezone.now()
        later = make_event(name="HackRU Spring", starts_at=now + timedelta(days=60), ends_at=now + timedelta(days=61), recruiting_ends_at=now + timedelta(days=60))
        sooner = make_event(name="HackRU Fall")
        make_event(name="Inactive", is_active=False)
        make_event(name="Finished", starts_at=now - timedelta(days=3), ends_at=now - timedelta(days=2), recruiting_ends_at=now - timedelta(days=3))
        self.login(make_user())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([event["slug"] for event in body], [sooner.slug, later.slug])
        self.assertEqual(
            set(body[0]),
            {"slug", "name", "description", "starts_at", "ends_at", "recruiting_ends_at", "is_recruiting"},
        )
        self.assertTrue(body[0]["is_recruiting"])

    def test_event_in_progress_is_listed_but_not_recruiting(self):
        now = timezone.now()
        make_event(name="Ongoing", starts_at=now - timedelta(hours=2), ends_at=now + timedelta(hours=20), recruiting_ends_at=now - timedelta(hours=2))
        self.login(make_user())

        body = self.client.get(self.url).json()

        self.assertEqual(len(body), 1)
        self.assertFalse(body[0]["is_recruiting"])

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
