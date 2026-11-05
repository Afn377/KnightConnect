from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from catalog.models import Event, Role

from ..models import Opportunity, OpportunityRole


def make_opportunity(owner, **overrides):
    fields = {
        "owner": owner,
        "title": "HackRU Teammates Needed",
        "description": "Looking for teammates for HackRU.",
        "opportunity_type": Opportunity.Type.HACKATHON,
        "commitment": "full_event",
        "availability": ["weekend_morning", "weekend_afternoon"],
        "expires_at": timezone.now() + timedelta(days=3),
    }
    fields.update(overrides)
    return Opportunity.objects.create(**fields)


class OpportunityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@rutgers.edu")

    def test_active_excludes_closed_and_past_expiry(self):
        active = make_opportunity(self.owner)
        make_opportunity(self.owner, title="Expired by time", expires_at=timezone.now() - timedelta(minutes=1))
        make_opportunity(self.owner, title="Closed").close(Opportunity.CloseReason.FILLED)

        self.assertQuerySetEqual(Opportunity.objects.active(), [active])

    def test_close_sets_status_reason_and_timestamp(self):
        opportunity = make_opportunity(self.owner)

        opportunity.close(Opportunity.CloseReason.EXPIRED)
        opportunity.refresh_from_db()

        self.assertEqual(opportunity.status, Opportunity.Status.EXPIRED)
        self.assertEqual(opportunity.close_reason, Opportunity.CloseReason.EXPIRED)
        self.assertIsNotNone(opportunity.closed_at)
        self.assertFalse(opportunity.is_active)

    def test_status_and_close_fields_must_agree(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_opportunity(self.owner, status=Opportunity.Status.CLOSED)

    def test_new_opportunity_must_expire_in_the_future_within_limit(self):
        opportunity = Opportunity(
            owner=self.owner,
            title="t",
            description="d",
            opportunity_type="other",
            commitment="light",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            opportunity.full_clean()

        opportunity.expires_at = timezone.now() + timedelta(days=45)
        with self.assertRaises(ValidationError):
            opportunity.full_clean()

        opportunity.expires_at = timezone.now() + timedelta(days=7)
        opportunity.full_clean()

    def test_expiry_cannot_pass_event_recruiting_deadline(self):
        now = timezone.now()
        event = Event.objects.create(
            name="HackRU",
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=3),
            recruiting_ends_at=now + timedelta(days=2),
        )
        opportunity = Opportunity(
            owner=self.owner,
            event=event,
            title="t",
            description="d",
            opportunity_type="hackathon",
            commitment="full_event",
            expires_at=now + timedelta(days=5),
        )

        with self.assertRaises(ValidationError):
            opportunity.full_clean()

    def test_role_listed_once_per_opportunity(self):
        opportunity = make_opportunity(self.owner)
        role = Role.objects.create(name="Backend developer")
        OpportunityRole.objects.create(opportunity=opportunity, role=role)

        with self.assertRaises(IntegrityError), transaction.atomic():
            OpportunityRole.objects.create(opportunity=opportunity, role=role)
