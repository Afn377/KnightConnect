from django.db import IntegrityError, transaction
from django.db.models import Q

from analytics.models import FunnelEvent
from core.exceptions import Conflict

from .models import ConnectionRequest


def send_request(*, opportunity, sender, recipient, kind, opportunity_role=None, message=""):
    """Create a pending request after checking it doesn't duplicate an existing connection."""
    candidate = sender if kind == ConnectionRequest.Kind.JOIN else recipient
    between_pair = Q(sender=sender, recipient=recipient) | Q(sender=recipient, recipient=sender)
    on_opportunity = ConnectionRequest.objects.filter(opportunity=opportunity)

    if on_opportunity.filter(between_pair, status=ConnectionRequest.Status.PENDING).exists():
        raise Conflict("There is already a pending request between you for this opportunity.")
    already_member = Q(kind=ConnectionRequest.Kind.JOIN, sender=candidate) | Q(
        kind=ConnectionRequest.Kind.INVITE, recipient=candidate
    )
    if on_opportunity.filter(already_member, status=ConnectionRequest.Status.ACCEPTED).exists():
        raise Conflict("This student is already on the team.")

    try:
        with transaction.atomic():
            request = ConnectionRequest.objects.create(
                opportunity=opportunity,
                opportunity_role=opportunity_role,
                kind=kind,
                sender=sender,
                recipient=recipient,
                message=message,
            )
    except IntegrityError:
        raise Conflict("There is already a pending request between you for this opportunity.")

    FunnelEvent.record(
        FunnelEvent.Type.REQUEST_SENT,
        user=sender,
        opportunity=opportunity,
        connection_request=request,
        kind=kind,
    )
    return request
