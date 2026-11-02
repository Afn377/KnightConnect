from datetime import timedelta

from django.utils import timezone

from analytics.models import FunnelEvent
from catalog.models import Role
from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user, throttle_rates
from opportunities.models import Opportunity, OpportunityRole
from safety.models import Block


class RequestFixtures:
    def make_world(self):
        self.owner = make_user(display_name="Owner")
        self.student = make_user(display_name="Student")
        self.opportunity = make_opportunity(owner=self.owner)
        self.backend = OpportunityRole.objects.create(
            opportunity=self.opportunity, role=Role.objects.create(name="Backend developer"), slots=1
        )

    def make_request(self, **fields):
        defaults = {"opportunity": self.opportunity, "kind": "join", "sender": self.student, "recipient": self.owner}
        defaults.update(fields)
        return ConnectionRequest.objects.create(**defaults)


class SendRequestTests(RequestFixtures, APITestCase):
    url = "/api/requests/"

    def setUp(self):
        super().setUp()
        self.make_world()

    def send(self, **data):
        payload = {"opportunity": str(self.opportunity.id)}
        payload.update(data)
        return self.client.post(self.url, payload, format="json")

    def test_student_sends_join_request_to_owner(self):
        self.login(self.student)

        response = self.send(role="backend-developer", message="I know Django!")

        self.assertEqual(response.status_code, 201, response.json())
        request = ConnectionRequest.objects.get()
        self.assertEqual(request.kind, "join")
        self.assertEqual(request.sender, self.student)
        self.assertEqual(request.recipient, self.owner)
        self.assertEqual(request.opportunity_role, self.backend)
        self.assertEqual(request.message, "I know Django!")
        self.assertEqual(request.status, "pending")
        body = response.json()
        self.assertEqual(body["id"], str(request.id))
        self.assertEqual(body["kind"], "join")
        self.assertEqual(body["direction"], "outgoing")
        self.assertEqual(body["opportunity"], {"id": str(self.opportunity.id), "title": self.opportunity.title, "status": "open"})
        self.assertEqual(body["role"], {"slug": "backend-developer", "name": "Backend developer"})
        self.assertEqual(body["sender"], {"id": str(self.student.id), "display_name": "Student"})
        self.assertEqual(body["recipient"], {"id": str(self.owner.id), "display_name": "Owner"})
        self.assertIsNone(body["contact_methods"])

    def test_owner_sends_invite_to_candidate(self):
        self.login(self.owner)

        response = self.send(recipient=str(self.student.id), role="backend-developer")

        self.assertEqual(response.status_code, 201, response.json())
        request = ConnectionRequest.objects.get()
        self.assertEqual(request.kind, "invite")
        self.assertEqual(request.sender, self.owner)
        self.assertEqual(request.recipient, self.student)

    def test_records_funnel_event(self):
        self.login(self.student)

        self.send()

        event = FunnelEvent.objects.get(event_type="request_sent")
        self.assertEqual(event.user, self.student)
        self.assertEqual(event.opportunity, self.opportunity)
        self.assertEqual(event.connection_request, ConnectionRequest.objects.get())
        self.assertEqual(event.metadata, {"kind": "join"})

    def test_invite_requires_recipient(self):
        self.login(self.owner)

        self.assertEqual(self.send().status_code, 400)

    def test_owner_cannot_invite_self(self):
        self.login(self.owner)

        self.assertEqual(self.send(recipient=str(self.owner.id)).status_code, 400)

    def test_invite_requires_candidate_open_to_requests(self):
        self.student.open_to_requests = False
        self.student.save()
        self.login(self.owner)

        self.assertEqual(self.send(recipient=str(self.student.id)).status_code, 400)

    def test_cannot_request_closed_or_expired_opportunity(self):
        self.login(self.student)
        self.opportunity.close(Opportunity.CloseReason.OWNER_CLOSED)

        self.assertEqual(self.send().status_code, 400)

        expired = make_opportunity(owner=self.owner, expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.send(opportunity=str(expired.id)).status_code, 400)

    def test_blocked_users_cannot_connect(self):
        Block.objects.create(blocker=self.owner, blocked=self.student)

        self.login(self.student)
        self.assertEqual(self.send().status_code, 400)

        self.login(self.owner)
        self.assertEqual(self.send(recipient=str(self.student.id)).status_code, 400)

    def test_cannot_invite_account_pending_deletion(self):
        self.student.deletion_scheduled_for = timezone.now() + timedelta(days=3)
        self.student.save()
        self.login(self.owner)

        self.assertEqual(self.send(recipient=str(self.student.id)).status_code, 400)

    def test_duplicate_pending_request_is_conflict(self):
        self.make_request()
        self.login(self.student)

        self.assertEqual(self.send().status_code, 409)

    def test_pending_request_in_other_direction_is_conflict(self):
        self.make_request(kind="invite", sender=self.owner, recipient=self.student)
        self.login(self.student)

        self.assertEqual(self.send().status_code, 409)

    def test_already_accepted_candidate_is_conflict(self):
        self.make_request(status="accepted")
        self.login(self.student)

        self.assertEqual(self.send().status_code, 409)

    def test_can_request_again_after_decline(self):
        self.make_request(status="declined")
        self.login(self.student)

        self.assertEqual(self.send().status_code, 201)

    def test_role_must_belong_to_opportunity(self):
        Role.objects.create(name="Designer")
        self.login(self.student)

        self.assertEqual(self.send(role="designer").status_code, 400)

    def test_role_must_have_open_slot(self):
        self.make_request(sender=make_user(), opportunity_role=self.backend, status="accepted")
        self.login(self.student)

        self.assertEqual(self.send(role="backend-developer").status_code, 400)

    def test_message_length_is_limited(self):
        self.login(self.student)

        self.assertEqual(self.send(message="x" * 501).status_code, 400)

    @throttle_rates(connection_request="2/day")
    def test_rate_limited(self):
        self.login(self.student)
        for _ in range(2):
            self.send(opportunity=str(make_opportunity().id))

        self.assertEqual(self.send().status_code, 429)

    def test_requires_authentication(self):
        self.assertEqual(self.send().status_code, 401)
