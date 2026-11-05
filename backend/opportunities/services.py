from django.core.exceptions import ValidationError
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


def publish_problems(opportunity):
    """What a draft is missing before it can be published, as {field: [messages]}."""
    problems = {}
    for field in ("title", "opportunity_type", "commitment", "expires_at"):
        if not getattr(opportunity, field):
            problems[field] = ["This field is required to publish."]
    if not opportunity.roles.exists():
        problems["roles"] = ["List at least one open role."]
    if opportunity.expires_at and opportunity.expires_at <= timezone.now():
        problems["expires_at"] = ["Expiry must be in the future."]
    if not problems:
        try:
            opportunity.clean()
        except ValidationError as error:
            problems.update(error.message_dict)
    if opportunity.event_id and not opportunity.event.is_recruiting:
        problems.setdefault("event", ["This event is no longer recruiting."])
    return problems


@transaction.atomic
def publish_opportunity(opportunity, *, actor):
    """Open a complete draft to requests. Raises ValidationError listing what's missing."""
    problems = publish_problems(opportunity)
    if problems:
        raise ValidationError(problems)
    opportunity.status = opportunity.Status.OPEN
    opportunity.published_at = timezone.now()
    opportunity.save(update_fields=["status", "published_at", "updated_at"])
    FunnelEvent.record(FunnelEvent.Type.OPPORTUNITY_CREATED, user=actor, opportunity=opportunity)
    return opportunity


@transaction.atomic
def delete_opportunity(opportunity):
    """Delete a post and its pending requests.

    Other requests (accepted connections and history) are kept; they keep
    the post title they were made for.
    """
    requests = opportunity.connection_requests.all()
    requests.filter(status=ConnectionRequest.Status.PENDING).delete()
    requests.filter(opportunity_title="").update(opportunity_title=opportunity.title)
    opportunity.delete()
