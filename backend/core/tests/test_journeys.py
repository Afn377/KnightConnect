"""End-to-end journeys through the API, across apps.

Each test drives one full user flow the way the frontend would: real sign-in
with an emailed code, profile setup, posting, matching, requests, and the
analytics that should come out the other side. Unit tests in each app cover
the edge cases; these make sure the pieces still fit together.
"""

import re
from datetime import timedelta

from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from analytics.models import FunnelEvent
from catalog.models import Interest, Role, Skill
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_event
from opportunities.models import Opportunity


class JourneyHelpers:
    def make_catalog(self):
        Role.objects.create(name="Backend developer")
        Role.objects.create(name="Designer")
        Skill.objects.create(name="Python")
        Skill.objects.create(name="Figma")
        Interest.objects.create(name="AI")
        self.event = make_event(name="HackRU Spring")

    def sign_in(self, email):
        """Sign in through the real code flow and return a client holding the session."""
        client = APIClient()
        response = client.post("/api/auth/request-code/", {"email": email}, format="json")
        self.assertEqual(response.status_code, 202, response.content)
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
        response = client.post("/api/auth/verify-code/", {"email": email, "code": code}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        client.last_sign_in = response.json()
        return client

    def set_up_profile(self, client, *, name, skills, roles, discord=None, **extra):
        profile = {
            "display_name": name,
            "availability": ["weekend_morning", "weekend_afternoon"],
            "commitment": "full",
            "skills": [{"skill": slug, "proficiency": "advanced"} for slug in skills],
            "preferred_roles": roles,
            "interests": ["ai"],
            **extra,
        }
        response = client.patch("/api/me/", profile, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        if discord:
            response = client.post("/api/me/contact-methods/", {"kind": "discord", "value": discord}, format="json")
            self.assertEqual(response.status_code, 201, response.content)
        return response

    def opportunity_payload(self, **overrides):
        data = {
            "title": "AI Study Buddy",
            "description": "An AI tutor for intro CS courses.",
            "opportunity_type": "hackathon",
            "event": "hackru-spring",
            "availability": ["weekend_morning", "weekend_afternoon"],
            "commitment": "full",
            "interests": ["ai"],
            "roles": [{"role": "backend-developer"}, {"role": "designer"}],
            "team_capacity": 3,
            "skills": [
                {"skill": "python", "requirement_type": "required"},
                {"skill": "figma", "requirement_type": "preferred"},
            ],
            "expires_at": (timezone.now() + timedelta(days=3)).isoformat(),
        }
        data.update(overrides)
        return data

    def post_opportunity(self, client, **overrides):
        response = client.post("/api/opportunities/", self.opportunity_payload(**overrides), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def candidate_ids(self, client, opportunity_id):
        response = client.get(f"/api/opportunities/{opportunity_id}/matches/")
        self.assertEqual(response.status_code, 200, response.content)
        return [item["candidate"]["id"] for item in response.json()["results"]]

    def browse_ids(self, client):
        response = client.get("/api/opportunities/")
        self.assertEqual(response.status_code, 200, response.content)
        return {item["id"] for item in response.json()["results"]}

    def funnel(self):
        staff = User.objects.create_user("staff@rutgers.edu", is_staff=True)
        client = APIClient()
        client.force_login(staff)
        response = client.get("/api/analytics/funnel/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["funnel"]


class JoinRequestJourneyTests(JourneyHelpers, APITestCase):
    """Post → match → request → accept → contact revealed → feedback → funnel."""

    def setUp(self):
        super().setUp()
        self.make_catalog()

    def test_full_join_request_loop(self):
        owner = self.sign_in("owner@rutgers.edu")
        student = self.sign_in("student@scarletmail.rutgers.edu")
        self.assertTrue(owner.last_sign_in["created"])
        self.set_up_profile(owner, name="Olivia Owner", skills=["figma"], roles=["designer"], discord="olivia.builds")
        self.set_up_profile(student, name="Sam Student", skills=["python"], roles=["backend-developer"], discord="sam.codes")
        outsider = self.sign_in("outsider@rutgers.edu")
        self.set_up_profile(outsider, name="No Python", skills=["figma"], roles=["designer"])

        opportunity = self.post_opportunity(owner)

        # The owner's Matches page lists the student, who has the required skill,
        # with an explanation, and leaves out the student who lacks it.
        response = owner.get(f"/api/opportunities/{opportunity['id']}/matches/")
        results = response.json()["results"]
        self.assertEqual([r["candidate"]["display_name"] for r in results], ["Sam Student"])
        self.assertTrue(results[0]["explanations"])
        self.assertTrue(response.json()["sparse"])

        # The student sees the post recommended and opens it.
        response = student.get("/api/recommendations/")
        recommendation = response.json()["results"][0]
        self.assertEqual(recommendation["opportunity"]["id"], opportunity["id"])
        response = student.post(
            "/api/analytics/track/",
            {"event_type": "recommendation_viewed", "match_result": recommendation["match_id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)

        # The student asks to join; nobody sees contact info yet.
        response = student.post(
            "/api/requests/",
            {"opportunity": opportunity["id"], "role": "backend-developer", "message": "I know Django."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        request_id = response.json()["id"]
        incoming = owner.get("/api/requests/", {"box": "incoming"}).json()["results"]
        self.assertEqual([r["id"] for r in incoming], [request_id])
        self.assertIsNone(incoming[0]["contact_methods"])

        # Accepting reveals each side's contact methods to the other and emails both.
        mail.outbox.clear()
        response = owner.post(f"/api/requests/{request_id}/accept/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["contact_methods"], [{"kind": "discord", "value": "sam.codes"}])
        detail = student.get(f"/api/requests/{request_id}/").json()
        self.assertEqual(detail["contact_methods"], [{"kind": "discord", "value": "olivia.builds"}])
        recipients = sorted(address for message in mail.outbox for address in message.to)
        self.assertEqual(recipients, ["owner@rutgers.edu", "student@scarletmail.rutgers.edu"])

        # The team roster now has two confirmed members, and the post is still recruiting.
        team = owner.get(f"/api/opportunities/{opportunity['id']}/team/")
        self.assertEqual(team.status_code, 200, team.content)
        self.assertEqual(Opportunity.objects.get(pk=opportunity["id"]).confirmed_count, 2)
        self.assertIn(opportunity["id"], self.browse_ids(outsider))

        # Both rate the connection, and the funnel report counts every step.
        for client in (owner, student):
            response = client.post(f"/api/requests/{request_id}/feedback/", {"was_useful": True}, format="json")
            self.assertEqual(response.status_code, 201, response.content)

        funnel = self.funnel()
        self.assertGreaterEqual(funnel["recommendations_shown"], 2)
        self.assertEqual(funnel["recommendations_viewed"], 1)
        self.assertEqual(funnel["requests_sent"], 1)
        self.assertEqual(funnel["requests_accepted"], 1)
        self.assertEqual(funnel["connections_rated"], 2)
        self.assertEqual(funnel["connections_rated_useful"], 2)


class InviteJourneyTests(JourneyHelpers, APITestCase):
    """Owner invites a recommended candidate; filling the team closes the post."""

    def setUp(self):
        super().setUp()
        self.make_catalog()

    def test_invite_fills_team_and_closes_post(self):
        owner = self.sign_in("owner@rutgers.edu")
        candidate = self.sign_in("candidate@rutgers.edu")
        browser = self.sign_in("browser@rutgers.edu")
        self.set_up_profile(owner, name="Owner", skills=["figma"], roles=["designer"])
        self.set_up_profile(candidate, name="Candidate", skills=["python"], roles=["backend-developer"], discord="cand")
        self.set_up_profile(browser, name="Browser", skills=["python"], roles=["backend-developer"])

        opportunity = self.post_opportunity(owner, team_capacity=2)
        candidate_id = str(User.objects.get(email="candidate@rutgers.edu").id)
        self.assertIn(candidate_id, self.candidate_ids(owner, opportunity["id"]))

        response = owner.post(
            "/api/requests/",
            {"opportunity": opportunity["id"], "recipient": candidate_id, "role": "backend-developer"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        invite_id = response.json()["id"]
        self.assertEqual(response.json()["kind"], "invite")

        # The invited candidate no longer appears as a fresh match while the invite is live.
        self.assertNotIn(candidate_id, self.candidate_ids(owner, opportunity["id"]))

        response = candidate.post(f"/api/requests/{invite_id}/accept/")
        self.assertEqual(response.status_code, 200, response.content)
        # The owner added no contact methods, so their Rutgers email is the fallback.
        self.assertEqual(response.json()["contact_methods"], [{"kind": "email", "value": "owner@rutgers.edu"}])

        # Owner + 1 member = capacity 2, so the post closes as filled and leaves browse.
        post = Opportunity.objects.get(pk=opportunity["id"])
        self.assertEqual((post.status, post.close_reason), ("closed", "filled"))
        self.assertNotIn(opportunity["id"], self.browse_ids(browser))
        response = browser.post("/api/requests/", {"opportunity": opportunity["id"]}, format="json")
        self.assertIn(response.status_code, (400, 404, 409), response.content)


class DraftToCloseJourneyTests(JourneyHelpers, APITestCase):
    """Draft → publish → request → owner closes early → pending request still reviewable → reopen."""

    def setUp(self):
        super().setUp()
        self.make_catalog()

    def test_draft_publish_close_and_reopen(self):
        owner = self.sign_in("owner@rutgers.edu")
        student = self.sign_in("student@rutgers.edu")
        late = self.sign_in("late@rutgers.edu")
        self.set_up_profile(owner, name="Owner", skills=["figma"], roles=["designer"])
        self.set_up_profile(student, name="Student", skills=["python"], roles=["backend-developer"])
        self.set_up_profile(late, name="Late", skills=["python"], roles=["backend-developer"])

        response = owner.post("/api/opportunities/", {"draft": True, "event": "hackru-spring"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        draft_id = response.json()["id"]
        self.assertNotIn(draft_id, self.browse_ids(student))

        payload = self.opportunity_payload()
        response = owner.patch(f"/api/opportunities/{draft_id}/", payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response = owner.post(f"/api/opportunities/{draft_id}/publish/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn(draft_id, self.browse_ids(student))
        self.assertEqual(FunnelEvent.objects.filter(event_type="opportunity_created", opportunity_id=draft_id).count(), 1)

        response = student.post("/api/requests/", {"opportunity": draft_id, "role": "backend-developer"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        request_id = response.json()["id"]

        # Closing early hides the post and stops new requests...
        response = owner.post(f"/api/opportunities/{draft_id}/close/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn(draft_id, self.browse_ids(late))
        response = late.post("/api/requests/", {"opportunity": draft_id}, format="json")
        self.assertIn(response.status_code, (400, 404, 409), response.content)

        # ...but the pending request can still be accepted before the deadline.
        response = owner.post(f"/api/requests/{request_id}/accept/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(ConnectionRequest.objects.get(pk=request_id).status, "accepted")

        # Reopening puts it back in browse for everyone else.
        response = owner.post(f"/api/opportunities/{draft_id}/reopen/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn(draft_id, self.browse_ids(late))


class AccountDeletionJourneyTests(JourneyHelpers, APITestCase):
    """Deleting an account hides it everywhere at once; signing in again restores it."""

    def setUp(self):
        super().setUp()
        self.make_catalog()

    def test_delete_then_restore(self):
        owner = self.sign_in("owner@rutgers.edu")
        student = self.sign_in("student@rutgers.edu")
        self.set_up_profile(owner, name="Owner", skills=["figma"], roles=["designer"])
        self.set_up_profile(student, name="Student", skills=["python"], roles=["backend-developer"])
        opportunity = self.post_opportunity(owner)
        student_id = str(User.objects.get(email="student@rutgers.edu").id)

        response = student.post("/api/requests/", {"opportunity": opportunity["id"]}, format="json")
        request_id = response.json()["id"]

        response = student.delete("/api/me/")
        self.assertEqual(response.status_code, 202, response.content)

        # Gone from matches and public profiles; their pending request is cancelled.
        self.assertNotIn(student_id, self.candidate_ids(owner, opportunity["id"]))
        self.assertEqual(owner.get(f"/api/users/{student_id}/").status_code, 404)
        self.assertEqual(ConnectionRequest.objects.get(pk=request_id).status, "cancelled")
        # The old session no longer works.
        self.assertEqual(student.get("/api/me/").status_code, 401)

        # Signing in within the grace period restores the account.
        student = self.sign_in("student@rutgers.edu")
        self.assertTrue(student.last_sign_in["restored"])
        self.assertIsNone(User.objects.get(pk=student_id).deletion_scheduled_for)
        self.assertEqual(owner.get(f"/api/users/{student_id}/").status_code, 200)
        self.assertIn(student_id, self.candidate_ids(owner, opportunity["id"]))
