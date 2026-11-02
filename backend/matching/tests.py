import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from opportunities.models import Opportunity

from .models import MatchResult


class MatchResultTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user("owner@rutgers.edu")
        self.candidate = User.objects.create_user("candidate@rutgers.edu")
        self.other = User.objects.create_user("other@rutgers.edu")
        self.opportunity = Opportunity.objects.create(
            owner=owner,
            title="t",
            description="d",
            opportunity_type="other",
            commitment="light",
            expires_at=timezone.now() + timedelta(days=3),
        )
        self.batch = uuid.uuid4()

    def result(self, candidate, rank):
        return MatchResult.objects.create(
            batch_id=self.batch,
            direction=MatchResult.Direction.CANDIDATES_FOR_OPPORTUNITY,
            opportunity=self.opportunity,
            candidate=candidate,
            rank=rank,
            score="0.750",
            explanation_factors=[{"factor": "skill", "label": "Backend experience", "weight": 0.3}],
        )

    def test_pair_appears_once_per_batch(self):
        self.result(self.candidate, 1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.result(self.candidate, 2)

    def test_rank_is_unique_per_batch(self):
        self.result(self.candidate, 1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.result(self.other, 1)
