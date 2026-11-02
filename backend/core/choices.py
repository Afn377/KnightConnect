"""Enumerations shared by profiles, opportunities, and matching."""

from django.db import models


class Commitment(models.TextChoices):
    """Expected time commitment.

    Ordered from lightest to heaviest so matching can compare levels by
    their position in ``Commitment.values``.
    """

    LIGHT = "light", "Light (under 5 hrs/week)"
    MODERATE = "moderate", "Moderate (5-10 hrs/week)"
    HEAVY = "heavy", "Heavy (10+ hrs/week)"
    FULL_EVENT = "full_event", "Full event (e.g. entire hackathon weekend)"


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
