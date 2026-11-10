from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from opportunities.models import Opportunity

from .models import FunnelEvent


class FunnelEventTests(TestCase):
    def test_record_stores_metadata(self):
        user = User.objects.create_user("student@rutgers.edu")

        event = FunnelEvent.record(FunnelEvent.Type.RECOMMENDATION_VIEWED, user=user, rank=2)

        self.assertEqual(event.metadata, {"rank": 2})
        self.assertEqual(event.user, user)

    def test_events_are_anonymized_when_user_is_deleted(self):
        user = User.objects.create_user("student@rutgers.edu")
        opportunity = Opportunity.objects.create(
            owner=user,
            title="t",
            description="d",
            opportunity_type="other",
            commitment="light",
            expires_at=timezone.now() + timedelta(days=1),
        )
        event = FunnelEvent.record(FunnelEvent.Type.OPPORTUNITY_CREATED, user=user, opportunity=opportunity)

        user.delete()
        event.refresh_from_db()

        self.assertIsNone(event.user)
        self.assertIsNone(event.opportunity)
        self.assertEqual(event.event_type, FunnelEvent.Type.OPPORTUNITY_CREATED)
