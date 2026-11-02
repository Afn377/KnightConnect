from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import UserSkill
from catalog.models import Interest, Role, Skill
from connections.models import ConnectionRequest
from core.testing import make_opportunity, make_user
from matching.engine import rank_candidates
from opportunities.models import OpportunityRole, OpportunitySkill
from safety.models import Block


class MatchingFixtures:
    def make_catalog(self):
        self.backend = Role.objects.create(name="Backend developer")
        self.designer = Role.objects.create(name="Designer")
        self.python = Skill.objects.create(name="Python")
        self.react = Skill.objects.create(name="React")
        self.figma = Skill.objects.create(name="Figma")
        self.ai = Interest.objects.create(name="AI")
        self.fintech = Interest.objects.create(name="Fintech")

    def make_student(self, skills=(), **fields):
        defaults = {"availability": ["weekend_morning"], "commitment": "full_event"}
        defaults.update(fields)
        student = make_user(**defaults)
        for skill in skills:
            UserSkill.objects.create(user=student, skill=skill)
        return student


class RankCandidatesTests(MatchingFixtures, TestCase):
    def setUp(self):
        self.make_catalog()
        self.owner = make_user()
        self.opportunity = make_opportunity(
            owner=self.owner,
            availability=["weekend_morning", "weekend_afternoon"],
            commitment="full_event",
            interests=[self.ai],
        )
        OpportunityRole.objects.create(opportunity=self.opportunity, role=self.backend, slots=1)
        OpportunitySkill.objects.create(opportunity=self.opportunity, skill=self.python, requirement_type="required")
        OpportunitySkill.objects.create(opportunity=self.opportunity, skill=self.react, requirement_type="preferred")

    def candidates(self):
        return [match.candidate for match in rank_candidates(self.opportunity)]

    def test_includes_students_meeting_every_requirement(self):
        student = self.make_student(skills=[self.python])

        self.assertEqual(self.candidates(), [student])

    def test_excludes_students_missing_a_required_skill(self):
        self.make_student(skills=[self.react])

        self.assertEqual(self.candidates(), [])

    def test_excludes_students_without_overlapping_availability(self):
        self.make_student(skills=[self.python], availability=["weekday_morning"])
        self.make_student(skills=[self.python], availability=[])

        self.assertEqual(self.candidates(), [])

    def test_availability_not_required_when_opportunity_lists_none(self):
        self.opportunity.availability = []
        self.opportunity.save()
        student = self.make_student(skills=[self.python], availability=[])

        self.assertEqual(self.candidates(), [student])

    def test_excludes_owner_and_students_not_open_to_requests(self):
        UserSkill.objects.create(user=self.owner, skill=self.python)
        self.owner.availability = ["weekend_morning"]
        self.owner.save()
        self.make_student(skills=[self.python], open_to_requests=False)

        self.assertEqual(self.candidates(), [])

    def test_excludes_blocked_disabled_and_deleting_accounts(self):
        blocked = self.make_student(skills=[self.python])
        Block.objects.create(blocker=blocked, blocked=self.owner)
        self.make_student(skills=[self.python], is_active=False)
        self.make_student(skills=[self.python], deletion_scheduled_for=timezone.now() + timedelta(days=1))

        self.assertEqual(self.candidates(), [])

    def test_excludes_students_already_pending_or_on_the_team(self):
        pending = self.make_student(skills=[self.python])
        member = self.make_student(skills=[self.python])
        declined = self.make_student(skills=[self.python])
        ConnectionRequest.objects.create(opportunity=self.opportunity, kind="join", sender=pending, recipient=self.owner)
        ConnectionRequest.objects.create(opportunity=self.opportunity, kind="invite", sender=self.owner, recipient=member, status="accepted")
        ConnectionRequest.objects.create(opportunity=self.opportunity, kind="join", sender=declined, recipient=self.owner, status="declined")

        self.assertEqual(self.candidates(), [declined])

    def test_better_fit_ranks_higher(self):
        basic = self.make_student(skills=[self.python], commitment="light")
        strong = self.make_student(
            skills=[self.python, self.react],
            preferred_roles=[self.backend],
            interests=[self.ai],
            availability=["weekend_morning", "weekend_afternoon"],
        )

        matches = rank_candidates(self.opportunity)

        self.assertEqual([match.candidate for match in matches], [strong, basic])
        self.assertGreater(matches[0].score, matches[1].score)
        self.assertLessEqual(matches[0].score, 1)
        self.assertGreaterEqual(matches[1].score, 0)

    def test_explains_the_ranking(self):
        self.make_student(
            skills=[self.python, self.react],
            preferred_roles=[self.backend],
            interests=[self.ai],
            availability=["weekend_morning"],
        )

        factors = rank_candidates(self.opportunity)[0].factors
        labels = [factor.label for factor in factors]

        self.assertIn("Python, React experience", labels)
        self.assertIn("Fits the Backend developer role", labels)
        self.assertIn("Interested in AI", labels)
        self.assertIn("Available weekend mornings", labels)
        self.assertIn("Same commitment level", labels)
        weights = [factor.weight for factor in factors]
        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_closed_opportunity_has_no_candidates(self):
        from opportunities.models import Opportunity

        self.make_student(skills=[self.python])
        self.opportunity.close(Opportunity.CloseReason.OWNER_CLOSED)

        self.assertEqual(self.candidates(), [])

    def test_limit(self):
        for _ in range(3):
            self.make_student(skills=[self.python])

        self.assertEqual(len(rank_candidates(self.opportunity, limit=2)), 2)
