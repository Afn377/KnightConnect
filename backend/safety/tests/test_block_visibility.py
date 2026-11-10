"""After a block, the two students disappear from each other everywhere.

The safety tests cover the block endpoints themselves; this sweeps every
other surface where one student can see another, in both directions.
"""

from catalog.models import Role, Skill
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from opportunities.models import OpportunityRole, OpportunitySkill
from safety.models import Block

SLOTS = ["weekend_morning", "weekend_afternoon"]


class BlockVisibilityTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name="Backend developer")
        self.python = Skill.objects.create(name="Python")
        # Each student owns a post the other would otherwise match.
        self.alice = self.make_student("alice@rutgers.edu")
        self.bob = self.make_student("bob@rutgers.edu")
        self.alice_post = self.make_post(self.alice)
        self.bob_post = self.make_post(self.bob)

    def make_student(self, email):
        user = make_user(email, display_name=email.split("@")[0], availability=SLOTS, commitment="full")
        user.user_skills.create(skill=self.python)
        user.preferred_roles.set([self.role])
        return user

    def make_post(self, owner):
        post = make_opportunity(owner=owner, availability=SLOTS)
        OpportunityRole.objects.create(opportunity=post, role=self.role)
        OpportunitySkill.objects.create(opportunity=post, skill=self.python, requirement_type="required")
        return post

    # What `viewer` can see of `other` and `other_post`, across every surface.
    def surfaces(self, viewer, other, other_post, own_post):
        self.login(viewer)
        browse = {item["id"] for item in self.client.get("/api/opportunities/").json()["results"]}
        recommended = {item["opportunity"]["id"] for item in self.client.get("/api/recommendations/").json()["results"]}
        matches = {
            item["candidate"]["id"]
            for item in self.client.get(f"/api/opportunities/{own_post.id}/matches/").json()["results"]
        }
        return {
            "browse": str(other_post.id) in browse,
            "recommendations": str(other_post.id) in recommended,
            "matches": str(other.id) in matches,
            "public_profile": self.client.get(f"/api/users/{other.id}/").status_code == 200,
            "opportunity_detail": self.client.get(f"/api/opportunities/{other_post.id}/").status_code == 200,
        }

    def assert_sees(self, expected):
        for viewer, other, other_post, own_post in (
            (self.alice, self.bob, self.bob_post, self.alice_post),
            (self.bob, self.alice, self.alice_post, self.bob_post),
        ):
            with self.subTest(viewer=viewer.email):
                seen = self.surfaces(viewer, other, other_post, own_post)
                self.assertEqual(seen, dict.fromkeys(seen, expected))

    def test_visible_to_each_other_before_a_block(self):
        self.assert_sees(True)

    def test_block_hides_both_ways_on_every_surface(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)

        self.assert_sees(False)

    def test_blocked_student_cannot_send_a_request_or_invite(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)

        self.login(self.bob)
        join = self.client.post("/api/requests/", {"opportunity": str(self.alice_post.id)}, format="json")
        invite = self.client.post(
            "/api/requests/", {"opportunity": str(self.bob_post.id), "recipient": str(self.alice.id)}, format="json"
        )

        self.assertGreaterEqual(join.status_code, 400)
        self.assertGreaterEqual(invite.status_code, 400)
        self.assertFalse(ConnectionRequest.objects.exists())

    def test_unblocking_restores_visibility(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)
        self.login(self.alice)
        self.assertEqual(self.client.delete(f"/api/blocks/{self.bob.id}/").status_code, 204)

        self.assert_sees(True)

    def test_blocking_through_the_api_hides_immediately(self):
        self.login(self.alice)
        response = self.client.post("/api/blocks/", {"user": str(self.bob.id)}, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        self.assert_sees(False)


class BlockAfterAcceptedConnectionTests(APITestCase):
    """What happens to an accepted connection once one side blocks the other.

    These tests document current behavior so a change to it is deliberate.
    """

    def setUp(self):
        super().setUp()
        self.owner = make_user("owner@rutgers.edu")
        self.member = make_user("member@rutgers.edu")
        self.member.contact_methods.create(kind="discord", value="member#1")
        self.owner.contact_methods.create(kind="discord", value="owner#1")
        post = make_opportunity(owner=self.owner)
        self.connection = ConnectionRequest.objects.create(
            opportunity=post, kind="join", sender=self.member, recipient=self.owner, status="accepted"
        )
        Block.objects.create(blocker=self.owner, blocked=self.member)

    def test_blocked_member_still_sees_blockers_contact_info(self):
        self.login(self.member)

        detail = self.client.get(f"/api/requests/{self.connection.id}/")

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["contact_methods"], [{"kind": "discord", "value": "owner#1"}])
