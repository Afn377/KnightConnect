from django.conf import settings
from django.core.mail import send_mail

from accounts.models import ContactMethod

from .contact import shared_contact_methods


def _describe(user):
    return user.display_name or "Your new teammate"


def send_connection_accepted_emails(connection_request):
    """Tell both participants they're connected and how to reach each other."""
    title = connection_request.opportunity_title or connection_request.opportunity.title
    pairs = (
        (connection_request.sender, connection_request.recipient),
        (connection_request.recipient, connection_request.sender),
    )
    for person, other in pairs:
        contact_lines = "\n".join(
            f"- {ContactMethod.Kind(method['kind']).label}: {method['value']}"
            for method in shared_contact_methods(other)
        )
        send_mail(
            subject=f"You're connected on KnightConnect: {title}",
            message=(
                f"Hi {person.display_name or 'there'},\n\n"
                f"You and {_describe(other)} are now connected about \"{title}\". "
                f"Here's how to reach them:\n\n{contact_lines}\n\n"
                "Good luck with your team!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[person.email],
        )
