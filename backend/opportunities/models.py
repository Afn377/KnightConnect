from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from catalog.models import Event, Interest, Role, Skill
from core.choices import Commitment, LocationType
from core.models import TimeStampedModel, UUIDModel
from core.validators import validate_availability_slots

MAX_OPPORTUNITY_LIFETIME = timedelta(days=30)


class OpportunityQuerySet(models.QuerySet):
    def active(self):
        """Open opportunities that have not passed their expiry time.

        Expiry is enforced at query time so an opportunity disappears from
        browse and matching the moment it expires, even before the periodic
        job flips its status to EXPIRED.
        """
        return self.filter(status=Opportunity.Status.OPEN, expires_at__gt=timezone.now())


class Opportunity(UUIDModel, TimeStampedModel):
    """A time-limited project or hackathon team that is recruiting."""

    class Type(models.TextChoices):
        HACKATHON = "hackathon", "Hackathon"
        CLASS_PROJECT = "class_project", "Class project"
        PERSONAL_PROJECT = "personal_project", "Personal project"
        RESEARCH = "research", "Research"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        EXPIRED = "expired", "Expired"

    class CloseReason(models.TextChoices):
        FILLED = "filled", "Team complete"
        OWNER_CLOSED = "owner_closed", "Closed by owner"
        EXPIRED = "expired", "Recruiting period ended"
        MODERATION = "moderation", "Removed by moderator"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="opportunities"
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="opportunities",
        help_text="Leave empty for projects not tied to a specific event.",
    )
    # Title, type, commitment, and expiry may be blank while the post is a draft;
    # serializers require them when creating or publishing a post.
    title = models.CharField(max_length=120, blank=True)
    description = models.TextField(
        max_length=4000, blank=True, help_text="Project overview: the track and what the team wants to build."
    )
    project_ideas = models.TextField(max_length=2000, blank=True)
    required_availability = models.CharField(
        max_length=300, blank=True, help_text="What the team needs, in the poster's words."
    )
    location_type = models.CharField(
        max_length=10, choices=LocationType.choices, default=LocationType.IN_PERSON
    )
    opportunity_type = models.CharField(max_length=20, choices=Type.choices, blank=True)
    availability = models.JSONField(
        default=list, blank=True, validators=[validate_availability_slots]
    )
    commitment = models.CharField(max_length=20, choices=Commitment.choices, blank=True)
    interests = models.ManyToManyField(Interest, blank=True, related_name="opportunities")
    skills = models.ManyToManyField(
        Skill, through="OpportunitySkill", blank=True, related_name="opportunities"
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    close_reason = models.CharField(max_length=20, choices=CloseReason.choices, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    team_capacity = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(2), MaxValueValidator(12)],
        help_text="Total team size, including the owner.",
    )
    draft_step = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="The step of the posting form a draft was saved on.",
    )

    objects = OpportunityQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "opportunities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"], name="opp_status_expires_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status__in=["open", "draft"], close_reason="", closed_at__isnull=True)
                    | (
                        ~models.Q(status__in=["open", "draft"])
                        & ~models.Q(close_reason="")
                        & models.Q(closed_at__isnull=False)
                    )
                ),
                name="opp_close_fields_match_status",
            ),
            models.CheckConstraint(
                condition=models.Q(status="draft") | models.Q(expires_at__isnull=False),
                name="opp_published_has_expiry",
            ),
            models.CheckConstraint(
                condition=models.Q(team_capacity__gte=2), name="opp_team_capacity_at_least_two"
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.expires_at is None:
            return
        now = timezone.now()
        if self._state.adding and self.expires_at <= now:
            raise ValidationError({"expires_at": "Expiry must be in the future."})
        # Measured from publication so repeated edits can't keep an opportunity open
        # indefinitely; a draft's clock starts when it is published.
        if self.status == self.Status.DRAFT:
            start = now
        else:
            start = self.published_at or self.created_at or now
        if self.expires_at > start + MAX_OPPORTUNITY_LIFETIME:
            raise ValidationError(
                {"expires_at": f"Opportunities can be open for at most {MAX_OPPORTUNITY_LIFETIME.days} days."}
            )
        if self.event_id and self.expires_at > self.event.recruiting_ends_at:
            raise ValidationError(
                {"expires_at": "Expiry cannot be after the event's recruiting deadline."}
            )

    @property
    def is_active(self):
        return (
            self.status == self.Status.OPEN
            and self.expires_at is not None
            and self.expires_at > timezone.now()
        )

    def accepted_members(self):
        return self.connection_requests.filter(status="accepted").count()

    @property
    def confirmed_count(self):
        """Confirmed team size: the owner plus accepted members."""
        accepted = getattr(self, "accepted_count", None)
        return 1 + (accepted if accepted is not None else self.accepted_members())

    @property
    def is_full(self):
        return self.confirmed_count >= self.team_capacity

    @property
    def can_accept_requests(self):
        """Whether pending requests can still be accepted.

        True while recruiting, and also after the owner closes recruiting
        early, until the original deadline passes.
        """
        if self.is_active:
            return True
        return (
            self.status == self.Status.CLOSED
            and self.close_reason == self.CloseReason.OWNER_CLOSED
            and self.expires_at is not None
            and self.expires_at > timezone.now()
        )

    def close(self, reason, *, save=True):
        status = self.Status.EXPIRED if reason == self.CloseReason.EXPIRED else self.Status.CLOSED
        self.status = status
        self.close_reason = reason
        self.closed_at = timezone.now()
        if save:
            self.save(update_fields=["status", "close_reason", "closed_at", "updated_at"])

    def reopen(self):
        self.status = self.Status.OPEN
        self.close_reason = ""
        self.closed_at = None
        self.save(update_fields=["status", "close_reason", "closed_at", "updated_at"])


class OpportunityRole(models.Model):
    """A role the team is looking for. Team size is set by Opportunity.team_capacity."""

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="opportunity_roles")
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["opportunity", "role"], name="opp_role_unique"),
        ]

    def __str__(self):
        return f"{self.opportunity}: {self.role}"


class OpportunitySkill(models.Model):
    class Requirement(models.TextChoices):
        REQUIRED = "required", "Required"
        PREFERRED = "preferred", "Preferred"

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="opportunity_skills")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="opportunity_skills")
    requirement_type = models.CharField(
        max_length=10, choices=Requirement.choices, default=Requirement.PREFERRED
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["opportunity", "skill"], name="opp_skill_unique"),
        ]

    def __str__(self):
        return f"{self.opportunity}: {self.skill} ({self.requirement_type})"
