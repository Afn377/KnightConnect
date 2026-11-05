"""Enumerations shared by profiles, opportunities, and matching."""

from django.db import models


class Commitment(models.TextChoices):
    """How much of an event (or project) a student can commit to, as on the posting form."""

    PARTIAL = "partial", "Partial availability"
    FULL = "full", "Full commitment"


class AvailabilitySlot(models.TextChoices):
    """Coarse weekly availability blocks.

    Profiles and opportunities each store a list of these so availability
    overlap can be computed as a set intersection.
    """

    WEEKDAY_MORNING = "weekday_morning", "Weekday mornings"
    WEEKDAY_AFTERNOON = "weekday_afternoon", "Weekday afternoons"
    WEEKDAY_EVENING = "weekday_evening", "Weekday evenings"
    WEEKEND_MORNING = "weekend_morning", "Weekend mornings"
    WEEKEND_AFTERNOON = "weekend_afternoon", "Weekend afternoons"
    WEEKEND_EVENING = "weekend_evening", "Weekend evenings"


class LocationType(models.TextChoices):
    IN_PERSON = "in_person", "In person"
    VIRTUAL = "virtual", "Virtual"
    HYBRID = "hybrid", "Hybrid"
