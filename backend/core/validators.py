from django.core.exceptions import ValidationError

from .choices import AvailabilitySlot


def validate_availability_slots(value):
    """Ensure an availability field is a list of unique, known slot codes."""
    if not isinstance(value, list):
        raise ValidationError("Availability must be a list of slots.")
    unknown = [slot for slot in value if slot not in AvailabilitySlot.values]
    if unknown:
        raise ValidationError(
            "Unknown availability slot(s): %(slots)s",
            params={"slots": ", ".join(map(str, unknown))},
        )
    if len(set(value)) != len(value):
        raise ValidationError("Availability slots must not repeat.")
