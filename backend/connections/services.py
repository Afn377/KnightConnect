from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from analytics.models import FunnelEvent
from core.exceptions import Conflict
from opportunities.models import Opportunity
from opportunities.services import close_opportunity

from .emails import send_connection_accepted_emails
from .models import ConnectionFeedback, ConnectionRequest


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


def _accepted_count(opportunity_role):
    return opportunity_role.connection_requests.filter(status=ConnectionRequest.Status.ACCEPTED).count()


def _all_roles_filled(opportunity):
    roles = opportunity.roles.annotate(
        filled=Count("connection_requests", filter=Q(connection_requests__status=ConnectionRequest.Status.ACCEPTED))
    )
    return roles.exists() and all(role.filled >= role.slots for role in roles)


def accept_request(connection_request, *, actor):
    """Accept a pending request, closing the opportunity once every role is filled.

    Both participants are emailed each other's contact details afterwards.
    """
    with transaction.atomic():
        opportunity = Opportunity.objects.select_for_update().get(pk=connection_request.opportunity_id)
        connection_request = ConnectionRequest.objects.select_for_update().get(pk=connection_request.pk)

        if connection_request.status != ConnectionRequest.Status.PENDING:
            raise Conflict("Only pending requests can be accepted.")
        if not opportunity.is_active:
            raise Conflict("This opportunity is no longer recruiting.")
        role = connection_request.opportunity_role
        if role is not None and _accepted_count(role) >= role.slots:
            raise Conflict("This role has already been filled.")

        connection_request.status = ConnectionRequest.Status.ACCEPTED
        connection_request.responded_at = timezone.now()
        connection_request.save(update_fields=["status", "responded_at", "updated_at"])
        FunnelEvent.record(
            FunnelEvent.Type.REQUEST_ACCEPTED,
            user=actor,
            opportunity=opportunity,
            connection_request=connection_request,
        )

        if _all_roles_filled(opportunity):
            close_opportunity(opportunity, Opportunity.CloseReason.FILLED)

    send_connection_accepted_emails(connection_request)
    return connection_request


def _resolve_pending(connection_request, *, status, event_type, actor):
    with transaction.atomic():
        connection_request = ConnectionRequest.objects.select_for_update().get(pk=connection_request.pk)
        if connection_request.status != ConnectionRequest.Status.PENDING:
            raise Conflict("Only pending requests can be changed.")
        connection_request.status = status
        connection_request.responded_at = timezone.now()
        connection_request.save(update_fields=["status", "responded_at", "updated_at"])
        FunnelEvent.record(
            event_type,
            user=actor,
            opportunity=connection_request.opportunity,
            connection_request=connection_request,
        )
    return connection_request


def decline_request(connection_request, *, actor):
    return _resolve_pending(
        connection_request,
        status=ConnectionRequest.Status.DECLINED,
        event_type=FunnelEvent.Type.REQUEST_DECLINED,
        actor=actor,
    )


def cancel_request(connection_request, *, actor):
    return _resolve_pending(
        connection_request,
        status=ConnectionRequest.Status.CANCELLED,
        event_type=FunnelEvent.Type.REQUEST_CANCELLED,
        actor=actor,
    )


def rate_connection(connection_request, *, user, was_useful, comment=""):
    """Record one participant's verdict on whether an accepted connection helped."""
    if connection_request.status != ConnectionRequest.Status.ACCEPTED:
        raise Conflict("Only accepted connections can be rated.")
    try:
        with transaction.atomic():
            feedback = ConnectionFeedback.objects.create(
                connection_request=connection_request, user=user, was_useful=was_useful, comment=comment
            )
    except IntegrityError:
        raise Conflict("You have already rated this connection.")
    FunnelEvent.record(
        FunnelEvent.Type.CONNECTION_RATED,
        user=user,
        opportunity=connection_request.opportunity,
        connection_request=connection_request,
        was_useful=was_useful,
    )
    return feedback
