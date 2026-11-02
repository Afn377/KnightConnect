from django.conf import settings
from django.core.exceptions import ValidationError


def is_allowed_email_domain(email):
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in {d.lower() for d in settings.ALLOWED_EMAIL_DOMAINS}


def validate_rutgers_email(email):
    if "@" not in email or not is_allowed_email_domain(email):
        allowed = ", ".join("@" + d for d in settings.ALLOWED_EMAIL_DOMAINS)
        raise ValidationError(
            "Use a Rutgers email address (%(allowed)s).",
            params={"allowed": allowed},
            code="invalid_domain",
        )
