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
        self.student = make_user(display_name="Student", major="Design", year="junior")
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
        self.assertEqual(
            body["sender"], {"id": str(self.student.id), "display_name": "Student", "major": "Design", "year": "junior"}
        )
        self.assertEqual(body["recipient"], {"id": str(self.owner.id), "display_name": "Owner", "major": "", "year": ""})
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


class ListRequestsTests(RequestFixtures, APITestCase):
    url = "/api/requests/"

    def setUp(self):
        super().setUp()
        self.make_world()
        self.outsider = make_user()
        self.incoming = self.make_request(sender=make_user(), recipient=self.owner)
        self.outgoing = self.make_request(kind="invite", sender=self.owner, recipient=self.student, status="declined")
        self.make_request(sender=self.outsider, recipient=make_user())
        self.login(self.owner)

    def ids(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return [item["id"] for item in response.json()["results"]]

    def test_lists_requests_involving_me_newest_first(self):
        self.assertEqual(self.ids(), [str(self.outgoing.id), str(self.incoming.id)])

    def test_filters_incoming_and_outgoing(self):
        self.assertEqual(self.ids(box="incoming"), [str(self.incoming.id)])
        self.assertEqual(self.ids(box="outgoing"), [str(self.outgoing.id)])

    def test_filters_by_status(self):
        self.assertEqual(self.ids(status="pending"), [str(self.incoming.id)])

    def test_marks_direction_from_my_side(self):
        results = self.client.get(self.url).json()["results"]

        self.assertEqual({item["id"]: item["direction"] for item in results}, {str(self.outgoing.id): "outgoing", str(self.incoming.id): "incoming"})

    def test_rejects_unknown_box(self):
        self.assertEqual(self.client.get(self.url, {"box": "spam"}).status_code, 400)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 401)


class RequestDetailTests(RequestFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.make_world()
        self.request_ = self.make_request(message="Hi!")

    def get(self):
        return self.client.get(f"/api/requests/{self.request_.id}/")

    def test_participants_can_view(self):
        for user in (self.owner, self.student):
            self.login(user)
            response = self.get()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["message"], "Hi!")

    def test_contact_methods_hidden_until_accepted(self):
        from accounts.models import ContactMethod

        ContactMethod.objects.create(user=self.owner, kind="discord", value="owner#1")
        self.login(self.student)
        self.assertIsNone(self.get().json()["contact_methods"])

        self.request_.status = "accepted"
        self.request_.save()

        self.assertEqual(self.get().json()["contact_methods"], [{"kind": "discord", "value": "owner#1"}])

    def test_falls_back_to_rutgers_email_without_contact_methods(self):
        self.request_.status = "accepted"
        self.request_.save()
        self.login(self.owner)

        self.assertEqual(self.get().json()["contact_methods"], [{"kind": "email", "value": self.student.email}])

    def test_outsiders_get_404(self):
        self.login(make_user())

        self.assertEqual(self.get().status_code, 404)

    def test_requires_authentication(self):
        self.assertEqual(self.get().status_code, 401)


class AcceptRequestTests(RequestFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.make_world()
        self.designer = OpportunityRole.objects.create(
            opportunity=self.opportunity, role=Role.objects.create(name="Designer"), slots=1
        )
        self.request_ = self.make_request(opportunity_role=self.backend)

    def accept(self, request=None):
        return self.client.post(f"/api/requests/{(request or self.request_).id}/accept/")

    def test_recipient_accepts(self):
        from accounts.models import ContactMethod

        ContactMethod.objects.create(user=self.student, kind="discord", value="student#1")
        self.login(self.owner)

        response = self.accept()

        self.assertEqual(response.status_code, 200)
        self.request_.refresh_from_db()
        self.assertEqual(self.request_.status, "accepted")
        self.assertIsNotNone(self.request_.responded_at)
        self.assertEqual(response.json()["contact_methods"], [{"kind": "discord", "value": "student#1"}])

    def test_student_accepts_invite(self):
        invite = self.make_request(kind="invite", sender=self.owner, recipient=make_user(), opportunity_role=self.designer)
        self.login(invite.recipient)

        self.assertEqual(self.accept(invite).status_code, 200)

    def test_records_funnel_event(self):
        self.login(self.owner)

        self.accept()

        event = FunnelEvent.objects.get(event_type="request_accepted")
        self.assertEqual(event.user, self.owner)
        self.assertEqual(event.connection_request, self.request_)

    def test_emails_both_participants_with_each_others_contact_details(self):
        from django.core import mail

        from accounts.models import ContactMethod

        ContactMethod.objects.create(user=self.owner, kind="discord", value="owner#1")
        ContactMethod.objects.create(user=self.student, kind="linkedin", value="linkedin.com/in/student")
        self.login(self.owner)

        self.accept()

        self.assertEqual(len(mail.outbox), 2)
        by_recipient = {message.to[0]: message for message in mail.outbox}
        to_student = by_recipient[self.student.email]
        to_owner = by_recipient[self.owner.email]
        self.assertIn(self.opportunity.title, to_student.subject + to_student.body)
        self.assertIn("owner#1", to_student.body)
        self.assertIn("Owner", to_student.body)
        self.assertIn("linkedin.com/in/student", to_owner.body)
        self.assertIn("Student", to_owner.body)
        self.assertNotIn("owner#1", to_owner.body)

    def test_closes_opportunity_when_every_role_is_filled(self):
        other_pending = self.make_request(sender=make_user())
        self.make_request(sender=make_user(), opportunity_role=self.designer, status="accepted")
        self.login(self.owner)

        self.accept()

        self.opportunity.refresh_from_db()
        other_pending.refresh_from_db()
        self.assertEqual(self.opportunity.status, "closed")
        self.assertEqual(self.opportunity.close_reason, "filled")
        self.assertEqual(other_pending.status, "expired")

    def test_keeps_opportunity_open_while_roles_remain(self):
        self.login(self.owner)

        self.accept()

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, "open")

    def test_sender_cannot_accept(self):
        self.login(self.student)

        self.assertEqual(self.accept().status_code, 403)

    def test_outsider_gets_404(self):
        self.login(make_user())

        self.assertEqual(self.accept().status_code, 404)

    def test_only_pending_requests_can_be_accepted(self):
        self.request_.status = "cancelled"
        self.request_.save()
        self.login(self.owner)

        self.assertEqual(self.accept().status_code, 409)

    def test_cannot_accept_for_inactive_opportunity(self):
        Opportunity.objects.filter(pk=self.opportunity.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.login(self.owner)

        self.assertEqual(self.accept().status_code, 409)
        self.request_.refresh_from_db()
        self.assertEqual(self.request_.status, "pending")

    def test_cannot_accept_into_full_role(self):
        self.make_request(sender=make_user(), opportunity_role=self.backend, status="accepted")
        self.login(self.owner)

        self.assertEqual(self.accept().status_code, 409)

    def test_requires_authentication(self):
        self.assertEqual(self.accept().status_code, 401)


class DeclineRequestTests(RequestFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.make_world()
        self.request_ = self.make_request()

    def decline(self):
        return self.client.post(f"/api/requests/{self.request_.id}/decline/")

    def test_recipient_declines(self):
        self.login(self.owner)

        response = self.decline()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "declined")
        self.request_.refresh_from_db()
        self.assertEqual(self.request_.status, "declined")
        self.assertIsNotNone(self.request_.responded_at)
        self.assertTrue(FunnelEvent.objects.filter(event_type="request_declined", connection_request=self.request_).exists())

    def test_sender_cannot_decline(self):
        self.login(self.student)

        self.assertEqual(self.decline().status_code, 403)

    def test_only_pending_requests_can_be_declined(self):
        self.request_.status = "accepted"
        self.request_.save()
        self.login(self.owner)

        self.assertEqual(self.decline().status_code, 409)

    def test_outsider_gets_404(self):
        self.login(make_user())

        self.assertEqual(self.decline().status_code, 404)


class CancelRequestTests(RequestFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.make_world()
        self.request_ = self.make_request()

    def cancel(self):
        return self.client.post(f"/api/requests/{self.request_.id}/cancel/")

    def test_sender_cancels(self):
        self.login(self.student)

        response = self.cancel()

        self.assertEqual(response.status_code, 200)
        self.request_.refresh_from_db()
        self.assertEqual(self.request_.status, "cancelled")
        self.assertTrue(FunnelEvent.objects.filter(event_type="request_cancelled", connection_request=self.request_).exists())

    def test_recipient_cannot_cancel(self):
        self.login(self.owner)

        self.assertEqual(self.cancel().status_code, 403)

    def test_only_pending_requests_can_be_cancelled(self):
        self.request_.status = "declined"
        self.request_.save()
        self.login(self.student)

        self.assertEqual(self.cancel().status_code, 409)


class ConnectionFeedbackTests(RequestFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.make_world()
        self.request_ = self.make_request(status="accepted")

    def rate(self, **data):
        payload = {"was_useful": True}
        payload.update(data)
        return self.client.post(f"/api/requests/{self.request_.id}/feedback/", payload, format="json")

    def test_participant_rates_connection(self):
        from connections.models import ConnectionFeedback

        self.login(self.student)

        response = self.rate(was_useful=False, comment="Never replied")

        self.assertEqual(response.status_code, 201)
        feedback = ConnectionFeedback.objects.get()
        self.assertEqual(feedback.user, self.student)
        self.assertFalse(feedback.was_useful)
        self.assertEqual(feedback.comment, "Never replied")
        self.assertEqual(response.json()["was_useful"], False)

    def test_both_participants_can_rate(self):
        self.login(self.student)
        self.assertEqual(self.rate().status_code, 201)

        self.login(self.owner)
        self.assertEqual(self.rate().status_code, 201)

    def test_records_funnel_event(self):
        self.login(self.owner)

        self.rate()

        event = FunnelEvent.objects.get(event_type="connection_rated")
        self.assertEqual(event.connection_request, self.request_)
        self.assertEqual(event.metadata, {"was_useful": True})

    def test_request_shows_my_feedback(self):
        self.login(self.student)
        self.assertIsNone(self.client.get(f"/api/requests/{self.request_.id}/").json()["my_feedback"])

        self.rate(comment="Great team")

        self.assertEqual(
            self.client.get(f"/api/requests/{self.request_.id}/").json()["my_feedback"],
            {"was_useful": True, "comment": "Great team"},
        )

    def test_can_only_rate_once(self):
        self.login(self.student)
        self.rate()

        self.assertEqual(self.rate().status_code, 409)

    def test_only_accepted_connections_can_be_rated(self):
        self.request_.status = "pending"
        self.request_.save()
        self.login(self.student)

        self.assertEqual(self.rate().status_code, 409)

    def test_was_useful_is_required(self):
        self.login(self.student)

        response = self.client.post(f"/api/requests/{self.request_.id}/feedback/", {}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_outsider_gets_404(self):
        self.login(make_user())

        self.assertEqual(self.rate().status_code, 404)
