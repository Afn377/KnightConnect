from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .emails import send_deletion_scheduled_email


def schedule_account_deletion(user):
    """Hide the account and schedule it for permanent deletion after the grace period.

    Pending connection requests involving the user are cancelled so nobody
    is left waiting on an account that is going away.
    """
    from connections.models import ConnectionRequest

    now = timezone.now()
    with transaction.atomic():
        user.deletion_scheduled_for = now + timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)
        user.save(update_fields=["deletion_scheduled_for", "updated_at"])

        ConnectionRequest.objects.filter(
            Q(sender=user) | Q(recipient=user), status=ConnectionRequest.Status.PENDING
        ).update(status=ConnectionRequest.Status.CANCELLED, responded_at=now, updated_at=now)

    send_deletion_scheduled_email(user)


def restore_account(user):
    """Cancel a scheduled deletion. Returns True if one was pending."""
    if user.deletion_scheduled_for is None:
        return False
    user.deletion_scheduled_for = None
    user.save(update_fields=["deletion_scheduled_for", "updated_at"])
    return True
