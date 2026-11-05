from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import UserSkill
from catalog.models import Interest, Role, Skill
from connections.models import ConnectionRequest
from core.testing import make_opportunity, make_user
from matching.engine import rank_candidates, rank_opportunities
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
        defaults = {"availability": ["weekend_morning"], "commitment": "full"}
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
            commitment="full",
            interests=[self.ai],
        )
        OpportunityRole.objects.create(opportunity=self.opportunity, role=self.backend)
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
        basic = self.make_student(skills=[self.python], commitment="partial")
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


class RankOpportunitiesTests(MatchingFixtures, TestCase):
    def setUp(self):
        self.make_catalog()
        self.student = self.make_student(
            skills=[self.python, self.react],
            preferred_roles=[self.backend],
            interests=[self.ai],
            availability=["weekend_morning", "weekend_afternoon"],
        )

    def post(self, required=(), preferred=(), roles=((None, 1),), **fields):
        defaults = {"availability": ["weekend_morning"], "commitment": "full"}
        defaults.update(fields)
        opportunity = make_opportunity(**defaults)
        for role, _ in roles:
            OpportunityRole.objects.create(opportunity=opportunity, role=role or self.backend)
        for skill in required:
            OpportunitySkill.objects.create(opportunity=opportunity, skill=skill, requirement_type="required")
        for skill in preferred:
            OpportunitySkill.objects.create(opportunity=opportunity, skill=skill, requirement_type="preferred")
        return opportunity

    def opportunities(self):
        return [match.opportunity for match in rank_opportunities(self.student)]

    def test_includes_opportunities_the_student_qualifies_for(self):
        opportunity = self.post(required=[self.python])

        self.assertEqual(self.opportunities(), [opportunity])
        self.assertEqual(rank_opportunities(self.student)[0].candidate, self.student)

    def test_excludes_missing_required_skill_and_no_availability_overlap(self):
        self.post(required=[self.figma])
        self.post(availability=["weekday_evening"])

        self.assertEqual(self.opportunities(), [])

    def test_excludes_own_closed_and_hidden_opportunities(self):
        from opportunities.models import Opportunity

        self.post(owner=self.student)
        self.post().close(Opportunity.CloseReason.OWNER_CLOSED)
        self.post(expires_at=timezone.now() - timedelta(minutes=1))
        blocked = self.post()
        Block.objects.create(blocker=blocked.owner, blocked=self.student)

        self.assertEqual(self.opportunities(), [])

    def test_excludes_opportunities_already_requested_or_joined(self):
        pending = self.post()
        joined = self.post()
        declined = self.post()
        ConnectionRequest.objects.create(opportunity=pending, kind="join", sender=self.student, recipient=pending.owner)
        ConnectionRequest.objects.create(opportunity=joined, kind="invite", sender=joined.owner, recipient=self.student, status="accepted")
        ConnectionRequest.objects.create(opportunity=declined, kind="join", sender=self.student, recipient=declined.owner, status="declined")

        self.assertEqual(self.opportunities(), [declined])

    def test_excludes_opportunities_with_a_full_team(self):
        full = self.post(team_capacity=2)
        ConnectionRequest.objects.create(
            opportunity=full, opportunity_role=full.roles.get(), kind="join", sender=make_user(), recipient=full.owner, status="accepted"
        )

        self.assertEqual(self.opportunities(), [])

    def test_better_fit_ranks_higher(self):
        weak = self.post(roles=[(self.designer, 1)], preferred=[self.figma], commitment="partial")
        strong = self.post(preferred=[self.react], interests=[self.ai], availability=["weekend_morning", "weekend_afternoon"])

        self.assertEqual(self.opportunities(), [strong, weak])

    def test_explains_the_ranking(self):
        self.post(preferred=[self.react], interests=[self.ai])

        labels = [factor.label for factor in rank_opportunities(self.student)[0].factors]

        self.assertIn("React experience", labels)
        self.assertIn("Fits the Backend developer role", labels)
        self.assertIn("Interested in AI", labels)


class SkillScoringTests(MatchingFixtures, TestCase):
    def setUp(self):
        self.make_catalog()
        self.opportunity = make_opportunity(availability=[], commitment="full")
        OpportunitySkill.objects.create(opportunity=self.opportunity, skill=self.python, requirement_type="required")
        OpportunitySkill.objects.create(opportunity=self.opportunity, skill=self.react, requirement_type="preferred")

    def student_with(self, *skills):
        student = make_user(availability=["weekend_morning"], commitment="full")
        for skill, proficiency in skills:
            UserSkill.objects.create(user=student, skill=skill, proficiency=proficiency)
        return student

    def scores(self):
        return {match.candidate: match.score for match in rank_candidates(self.opportunity)}

    def test_higher_proficiency_scores_higher(self):
        advanced = self.student_with((self.python, "advanced"), (self.react, "advanced"))
        beginner = self.student_with((self.python, "beginner"), (self.react, "beginner"))

        scores = self.scores()

        self.assertGreater(scores[advanced], scores[beginner])

    def test_required_skills_weigh_more_than_preferred(self):
        strong_required = self.student_with((self.python, "advanced"))
        weak_both = self.student_with((self.python, "beginner"), (self.react, "beginner"))

        scores = self.scores()

        self.assertGreater(scores[strong_required], scores[weak_both])

    def test_skill_factor_applies_with_only_required_skills(self):
        OpportunitySkill.objects.filter(requirement_type="preferred").delete()
        advanced = self.student_with((self.python, "advanced"))
        beginner = self.student_with((self.python, "beginner"))

        scores = self.scores()

        self.assertGreater(scores[advanced], scores[beginner])


class InterestedEventScoringTests(MatchingFixtures, TestCase):
    def test_students_going_to_the_event_rank_higher_and_are_told_why(self):
        from core.testing import make_event

        event = make_event(name="HackRU Spring")
        opportunity = make_opportunity(event=event, availability=[])
        going = self.make_student()
        going.interested_events.set([event])
        not_going = self.make_student()

        matches = rank_candidates(opportunity)

        self.assertEqual([match.candidate for match in matches], [going, not_going])
        self.assertIn("Going to HackRU Spring", [factor.label for factor in matches[0].factors])


class CommitmentScoringTests(MatchingFixtures, TestCase):
    def test_meeting_the_commitment_scores_higher_than_falling_short(self):
        full_post = make_opportunity(availability=[], commitment="full")
        full_student = self.make_student(commitment="full")
        partial_student = self.make_student(commitment="partial")

        scores = {match.candidate: match for match in rank_candidates(full_post)}

        self.assertGreater(scores[full_student].score, scores[partial_student].score)
        self.assertIn("Same commitment level", [f.label for f in scores[full_student].factors])

    def test_full_commitment_satisfies_a_partial_post(self):
        partial_post = make_opportunity(availability=[], commitment="partial")
        full_student = self.make_student(commitment="full")

        labels = [f.label for f in rank_candidates(partial_post)[0].factors]

        self.assertIn("Can commit to the full event", labels)
