from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from opportunities.models import Opportunity

from ..models import ConnectionFeedback, ConnectionRequest


class ConnectionRequestTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@rutgers.edu")
        self.student = User.objects.create_user("student@scarletmail.rutgers.edu")
        self.other = User.objects.create_user("other@rutgers.edu")
        self.opportunity = Opportunity.objects.create(
            owner=self.owner,
            title="HackRU Teammates Needed",
            description="d",
            opportunity_type="hackathon",
            commitment="full_event",
            expires_at=timezone.now() + timedelta(days=3),
        )

    def request(self, **overrides):
        fields = {
            "opportunity": self.opportunity,
            "kind": ConnectionRequest.Kind.JOIN,
            "sender": self.student,
            "recipient": self.owner,
        }
        fields.update(overrides)
        return ConnectionRequest(**fields)

    def test_candidate_depends_on_direction(self):
        join = self.request()
        invite = self.request(kind=ConnectionRequest.Kind.INVITE, sender=self.owner, recipient=self.student)

        self.assertEqual(join.candidate, self.student)
        self.assertEqual(invite.candidate, self.student)

    def test_join_must_target_owner(self):
        with self.assertRaises(ValidationError):
            self.request(recipient=self.other).full_clean()

    def test_invite_must_come_from_owner(self):
        with self.assertRaises(ValidationError):
            self.request(kind=ConnectionRequest.Kind.INVITE, sender=self.other, recipient=self.student).full_clean()

    def test_cannot_request_self(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.request(sender=self.owner, recipient=self.owner).save()

    def test_only_one_pending_request_per_pair(self):
        self.request().save()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.request().save()

    def test_new_request_allowed_after_previous_declined(self):
        first = self.request()
        first.save()
        first.status = ConnectionRequest.Status.DECLINED
        first.save()

        self.request().save()


class ConnectionFeedbackTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@rutgers.edu")
        self.student = User.objects.create_user("student@rutgers.edu")
        opportunity = Opportunity.objects.create(
            owner=self.owner,
            title="t",
            description="d",
            opportunity_type="other",
            commitment="light",
            expires_at=timezone.now() + timedelta(days=3),
        )
        self.connection = ConnectionRequest.objects.create(
            opportunity=opportunity, kind="join", sender=self.student, recipient=self.owner
        )

    def test_feedback_requires_accepted_connection(self):
        feedback = ConnectionFeedback(connection_request=self.connection, user=self.student, was_useful=True)
        with self.assertRaises(ValidationError):
            feedback.full_clean()

        self.connection.status = ConnectionRequest.Status.ACCEPTED
        self.connection.save()
        feedback.full_clean()

    def test_feedback_only_from_participants(self):
        self.connection.status = ConnectionRequest.Status.ACCEPTED
        self.connection.save()
        outsider = User.objects.create_user("outsider@rutgers.edu")

        with self.assertRaises(ValidationError):
            ConnectionFeedback(connection_request=self.connection, user=outsider, was_useful=True).full_clean()
