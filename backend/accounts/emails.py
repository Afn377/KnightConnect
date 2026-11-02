from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def send_login_code_email(email, code):
    send_mail(
        subject=f"Your KnightConnect sign-in code: {code}",
        message=(
            f"Your KnightConnect sign-in code is {code}.\n\n"
            f"It expires in {settings.LOGIN_CODE_TTL_MINUTES} minutes. "
            "If you didn't request it, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def send_deletion_scheduled_email(user):
    days = settings.ACCOUNT_DELETION_GRACE_DAYS
    deadline = timezone.localtime(user.deletion_scheduled_for).strftime("%B %-d, %Y at %-I:%M %p %Z")
    send_mail(
        subject="Your KnightConnect account is scheduled for deletion",
        message=(
            f"We received a request to delete your KnightConnect account ({user.email}).\n\n"
            f"Your account is now hidden and will be permanently deleted in {days} days, "
            f"on {deadline}.\n\n"
            "Changed your mind? Sign in again before then and your account will be "
            "restored automatically."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
