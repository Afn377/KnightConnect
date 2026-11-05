"""Deterministic, explainable matching between students and opportunities.

Matching runs in three steps:

1. Required filters remove pairings that can't work: missing a required
   skill, no overlapping availability, inactive or blocked accounts, and
   students already pending or accepted on the opportunity.
2. A weighted score ranks what remains using skills (required ones count
   double, scaled by proficiency), role fit,
   availability overlap, shared interests, and commitment closeness
   (weights in settings.MATCHING_WEIGHTS).
3. Each factor that contributed becomes a human-readable explanation.
"""

from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Q

from accounts.models import User
from connections.models import ConnectionRequest
from core.choices import AvailabilitySlot, Commitment
from opportunities.models import OpportunitySkill
from opportunities.queries import browsable_by, with_details

LIVE_STATUSES = [ConnectionRequest.Status.PENDING, ConnectionRequest.Status.ACCEPTED]

# A required skill counts this many times as much as a preferred one in the skill score.
REQUIRED_SKILL_WEIGHT = 2
PREFERRED_SKILL_WEIGHT = 1
PROFICIENCY_VALUE = {"beginner": 0.6, "intermediate": 0.8, "advanced": 1.0}


@dataclass(frozen=True)
class Factor:
    factor: str
    label: str
    weight: float

    def as_dict(self):
        return {"factor": self.factor, "label": self.label, "weight": self.weight}


@dataclass
class Match:
    opportunity: object
    candidate: object
    score: float
    factors: list = field(default_factory=list)


@dataclass
class Requirements:
    required_skills: dict
    preferred_skills: dict
    open_roles: dict
    interests: dict
    availability: set
    commitment: str


@dataclass
class Profile:
    skills: dict
    proficiency: dict
    roles: set
    interests: set
    availability: set
    commitment: str


def requirements_for(opportunity):
    skills = list(opportunity.opportunity_skills.all())
    return Requirements(
        required_skills={
            s.skill_id: s.skill.name for s in skills if s.requirement_type == OpportunitySkill.Requirement.REQUIRED
        },
        preferred_skills={
            s.skill_id: s.skill.name for s in skills if s.requirement_type == OpportunitySkill.Requirement.PREFERRED
        },
        open_roles={
            r.role_id: r.role.name for r in opportunity.roles.all() if getattr(r, "filled", 0) < r.slots
        },
        interests={i.pk: i.name for i in opportunity.interests.all()},
        availability=set(opportunity.availability or []),
        commitment=opportunity.commitment,
    )


def profile_for(user):
    return Profile(
        skills={us.skill_id: us.skill.name for us in user.user_skills.all()},
        proficiency={us.skill_id: us.proficiency for us in user.user_skills.all()},
        roles={r.pk for r in user.preferred_roles.all()},
        interests={i.pk for i in user.interests.all()},
        availability=set(user.availability or []),
        commitment=user.commitment,
    )


def passes_required_filters(requirements, profile):
    if not set(requirements.required_skills) <= set(profile.skills):
        return False
    if requirements.availability and not (requirements.availability & profile.availability):
        return False
    return True


def _join(names):
    names = sorted(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _availability_label(slots):
    ordered = [slot for slot in AvailabilitySlot.values if slot in slots]
    labels = [AvailabilitySlot(slot).label.lower() for slot in ordered]
    if len(labels) <= 2:
        return "Available " + " and ".join(labels)
    return "Available " + ", ".join(labels[:-1]) + " and " + labels[-1]


def score(requirements, profile):
    """Return (score between 0 and 1, explanation factors ordered by contribution)."""
    weights = settings.MATCHING_WEIGHTS
    parts = []  # (factor, weight, value, label)

    matched_skills = {
        skill_id: name
        for skill_id, name in profile.skills.items()
        if skill_id in requirements.required_skills or skill_id in requirements.preferred_skills
    }
    skill_label = f"{', '.join(sorted(matched_skills.values()))} experience" if matched_skills else ""
    skill_weights = {skill_id: REQUIRED_SKILL_WEIGHT for skill_id in requirements.required_skills}
    skill_weights.update({skill_id: PREFERRED_SKILL_WEIGHT for skill_id in requirements.preferred_skills})
    if skill_weights:
        earned = sum(
            weight * PROFICIENCY_VALUE.get(profile.proficiency.get(skill_id), 0)
            for skill_id, weight in skill_weights.items()
            if skill_id in profile.skills
        )
        parts.append(("skills", weights["skills"], earned / sum(skill_weights.values()), skill_label))

    if requirements.open_roles:
        fitting = [name for role_id, name in requirements.open_roles.items() if role_id in profile.roles]
        label = f"Fits the {_join(fitting)} role" if fitting else ""
        parts.append(("role", weights["role"], 1.0 if fitting else 0.0, label))

    if requirements.availability:
        overlap = requirements.availability & profile.availability
        parts.append(
            ("availability", weights["availability"], len(overlap) / len(requirements.availability), _availability_label(overlap) if overlap else "")
        )

    if requirements.interests:
        shared = [name for interest_id, name in requirements.interests.items() if interest_id in profile.interests]
        label = f"Interested in {_join(shared)}" if shared else ""
        parts.append(("interests", weights["interests"], len(shared) / len(requirements.interests), label))

    if requirements.commitment and profile.commitment:
        order = Commitment.values
        distance = abs(order.index(requirements.commitment) - order.index(profile.commitment))
        value = max(0.0, 1 - distance / (len(order) - 1))
        label = "Same commitment level" if distance == 0 else ("Similar commitment level" if distance == 1 else "")
        parts.append(("commitment", weights["commitment"], value, label))

    total_weight = sum(weight for _, weight, _, _ in parts)
    if total_weight == 0:
        total = 0.0
    else:
        total = sum(weight * value for _, weight, value, _ in parts) / total_weight

    factors = [
        Factor(name, label, round(weight * value / total_weight, 3) if total_weight else 0.0)
        for name, weight, value, label in parts
        if label
    ]
    factors.sort(key=lambda factor: factor.weight, reverse=True)
    return round(total, 3), factors


def _profile_prefetches(queryset):
    return queryset.prefetch_related("user_skills__skill", "preferred_roles", "interests")


def rank_candidates(opportunity, *, limit=None):
    """Rank students who could join ``opportunity``, best fit first."""
    limit = limit or settings.MATCHING_RESULT_LIMIT
    opportunity = with_details(type(opportunity).objects.filter(pk=opportunity.pk)).get()
    if not opportunity.is_active:
        return []

    involved = ConnectionRequest.objects.filter(opportunity=opportunity, status__in=LIVE_STATUSES)
    excluded_ids = set(involved.values_list("sender", flat=True)) | set(involved.values_list("recipient", flat=True))
    excluded_ids.add(opportunity.owner_id)

    candidates = _profile_prefetches(
        User.objects.visible_to(opportunity.owner).filter(open_to_requests=True).exclude(pk__in=excluded_ids)
    )

    requirements = requirements_for(opportunity)
    matches = []
    for candidate in candidates.order_by("created_at", "id"):
        profile = profile_for(candidate)
        if not passes_required_filters(requirements, profile):
            continue
        total, factors = score(requirements, profile)
        matches.append(Match(opportunity=opportunity, candidate=candidate, score=total, factors=factors))

    matches.sort(key=lambda match: match.score, reverse=True)
    return matches[:limit]


def rank_opportunities(student, *, limit=None):
    """Rank open opportunities ``student`` could join, best fit first."""
    limit = limit or settings.MATCHING_RESULT_LIMIT
    already_involved = ConnectionRequest.objects.filter(
        Q(sender=student) | Q(recipient=student), status__in=LIVE_STATUSES
    ).values("opportunity")
    opportunities = with_details(
        browsable_by(student).exclude(owner=student).exclude(pk__in=already_involved)
    ).order_by("-created_at")

    student = _profile_prefetches(User.objects.filter(pk=student.pk)).get()
    profile = profile_for(student)
    matches = []
    for opportunity in opportunities:
        requirements = requirements_for(opportunity)
        if not requirements.open_roles or not passes_required_filters(requirements, profile):
            continue
        total, factors = score(requirements, profile)
        matches.append(Match(opportunity=opportunity, candidate=student, score=total, factors=factors))

    matches.sort(key=lambda match: match.score, reverse=True)
    return matches[:limit]
