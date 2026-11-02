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
