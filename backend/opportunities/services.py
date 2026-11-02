from django.db import transaction
from django.utils import timezone

from analytics.models import FunnelEvent
from connections.models import ConnectionRequest


@transaction.atomic
def close_opportunity(opportunity, reason, *, actor=None):
    """Close an opportunity and expire its pending connection requests.

    Accepted connections are left untouched.
    """
    opportunity.close(reason)
    now = timezone.now()
    opportunity.connection_requests.filter(status=ConnectionRequest.Status.PENDING).update(
        status=ConnectionRequest.Status.EXPIRED, responded_at=now, updated_at=now
    )
    FunnelEvent.record(
        FunnelEvent.Type.OPPORTUNITY_CLOSED, user=actor, opportunity=opportunity, reason=reason
    )
    return opportunity
