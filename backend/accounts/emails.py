from django.conf import settings
from django.core.mail import send_mail


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
