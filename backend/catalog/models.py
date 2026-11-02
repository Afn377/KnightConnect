"""Shared vocabularies that profiles and opportunities refer to.

Keeping skills, roles, and interests as rows (rather than free text) lets
matching compare them exactly and lets the browse page filter on them.
"""

from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.text import slugify

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


class Event(TimeStampedModel):
    """A hackathon or other recruiting window that opportunities belong to."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    recruiting_ends_at = models.DateTimeField(
        help_text="Opportunities tied to this event expire no later than this time.",
    )
    is_active = models.BooleanField(default=True)

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
    def is_recruiting(self):
        return self.is_active and timezone.now() < self.recruiting_ends_at

    def __str__(self):
        return self.name
