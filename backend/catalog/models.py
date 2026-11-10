"""Shared vocabularies that profiles and opportunities refer to.

Keeping skills, roles, and interests as rows (rather than free text) lets
matching compare them exactly and lets the browse page filter on them.
"""

from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.text import slugify

from core.choices import LocationType
from core.models import TimeStampedModel


class SluggedName(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64, unique=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Skill(SluggedName):
    """A concrete technical or non-technical skill, e.g. "React" or "Figma"."""

    class Meta(SluggedName.Meta):
        constraints = [
            models.UniqueConstraint(Lower("name"), name="catalog_skill_name_ci_unique"),
        ]


class Role(SluggedName):
    """A position on a team, e.g. "Backend developer" or "Designer"."""

    class Meta(SluggedName.Meta):
        constraints = [
            models.UniqueConstraint(Lower("name"), name="catalog_role_name_ci_unique"),
        ]


class Interest(SluggedName):
    """A topic or domain, e.g. "AI/ML" or "Fintech"."""

    class Meta(SluggedName.Meta):
        constraints = [
            models.UniqueConstraint(Lower("name"), name="catalog_interest_name_ci_unique"),
        ]


class EventQuerySet(models.QuerySet):
    def with_status(self, status):
        now = timezone.now()
        if status == Event.Status.UPCOMING:
            return self.filter(starts_at__gt=now)
        if status == Event.Status.ONGOING:
            return self.filter(starts_at__lte=now, ends_at__gt=now)
        if status == Event.Status.PAST:
            return self.filter(ends_at__lte=now)
        return self.none()


class Event(TimeStampedModel):
    """A hackathon or other recruiting window that opportunities belong to."""

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ONGOING = "ongoing", "Ongoing"
        PAST = "past", "Past"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    recruiting_ends_at = models.DateTimeField(
        help_text="Opportunities tied to this event expire no later than this time.",
    )
    is_active = models.BooleanField(default=True)
    location_type = models.CharField(
        max_length=10, choices=LocationType.choices, default=LocationType.IN_PERSON
    )
    venue = models.CharField(max_length=120, blank=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gte=models.F("starts_at")),
                name="catalog_event_ends_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(recruiting_ends_at__lte=models.F("ends_at")),
                name="catalog_event_recruiting_ends_before_event_end",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def status(self):
        now = timezone.now()
        if now < self.starts_at:
            return self.Status.UPCOMING
        if now < self.ends_at:
            return self.Status.ONGOING
        return self.Status.PAST

    @property
    def is_recruiting(self):
        return self.is_active and timezone.now() < self.recruiting_ends_at

    def __str__(self):
        return self.name
