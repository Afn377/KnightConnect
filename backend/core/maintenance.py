from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from accounts.models import LoginCode, User
from opportunities.models import Opportunity
from connections.models import ConnectionRequest
from opportunities.services import close_opportunity, expire_pending_requests

LOGIN_CODE_RETENTION = timedelta(days=1)


def expire_opportunities():
    due = Opportunity.objects.filter(status=Opportunity.Status.OPEN, expires_at__lte=timezone.now())
    count = 0
    for opportunity in due:
        close_opportunity(opportunity, Opportunity.CloseReason.EXPIRED)
        count += 1
    # Posts the owner closed early keep pending requests reviewable only until the deadline.
    expire_pending_requests(
        ConnectionRequest.objects.filter(opportunity__expires_at__lte=timezone.now())
    )
    return count


def delete_accounts_past_grace_period():
    """Permanently delete accounts whose recovery window has passed.

    Funnel events and reports they filed survive anonymized (SET_NULL).
    """
    due = User.objects.filter(deletion_scheduled_for__lte=timezone.now())
    count = due.count()
    for user in due:
        user.delete()
    return count


def purge_login_codes():
    cutoff = timezone.now() - LOGIN_CODE_RETENTION
    deleted, _ = LoginCode.objects.filter(Q(expires_at__lt=cutoff) | Q(consumed_at__lt=cutoff)).delete()
    return deleted


def run_maintenance():
    return {
        "expired_opportunities": expire_opportunities(),
        "deleted_accounts": delete_accounts_past_grace_period(),
        "purged_login_codes": purge_login_codes(),
    }
