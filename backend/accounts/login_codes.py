import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .emails import send_login_code_email
from .models import LoginCode


def hash_code(email, code):
    message = f"{email}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def generate_code():
    return "".join(secrets.choice("0123456789") for _ in range(settings.LOGIN_CODE_LENGTH))


def issue_login_code(email):
    """Create a fresh code for ``email``, replacing any outstanding one, and email it."""
    code = generate_code()
    with transaction.atomic():
        LoginCode.objects.filter(email=email, consumed_at__isnull=True).delete()
        LoginCode.objects.create(
            email=email,
            code_hash=hash_code(email, code),
            expires_at=timezone.now() + timedelta(minutes=settings.LOGIN_CODE_TTL_MINUTES),
        )
    send_login_code_email(email, code)


class InvalidLoginCode(Exception):
    pass


def verify_login_code(email, code):
    """Consume the outstanding code for ``email`` if ``code`` matches.

    Raises InvalidLoginCode when there is no usable code or it does not
    match. Failed attempts are counted, and the code stops working after
    LOGIN_CODE_MAX_ATTEMPTS failures.
    """
    with transaction.atomic():
        login_code = (
            LoginCode.objects.select_for_update()
            .filter(email=email, consumed_at__isnull=True)
            .first()
        )
        if login_code is None or login_code.expires_at <= timezone.now():
            error = "This code has expired. Request a new one."
        elif login_code.attempts >= settings.LOGIN_CODE_MAX_ATTEMPTS:
            error = "Too many incorrect attempts. Request a new code."
        elif not hmac.compare_digest(login_code.code_hash, hash_code(email, code)):
            login_code.attempts += 1
            login_code.save(update_fields=["attempts"])
            error = "Incorrect code."
        else:
            login_code.consumed_at = timezone.now()
            login_code.save(update_fields=["consumed_at"])
            error = None

    if error:
        raise InvalidLoginCode(error)
