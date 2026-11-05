from django.db.models import Count, Q

from .models import FunnelEvent

Type = FunnelEvent.Type


def funnel_counts(start=None, end=None):
    """Count each discovery funnel step, optionally within an inclusive local-date range."""
    events = FunnelEvent.objects.all()
    if start:
        events = events.filter(occurred_at__date__gte=start)
    if end:
        events = events.filter(occurred_at__date__lte=end)

    return events.aggregate(
        recommendations_shown=Count("id", filter=Q(event_type=Type.RECOMMENDATION_SHOWN)),
        recommendations_viewed=Count("id", filter=Q(event_type=Type.RECOMMENDATION_VIEWED)),
        requests_sent=Count("id", filter=Q(event_type=Type.REQUEST_SENT)),
        requests_accepted=Count("id", filter=Q(event_type=Type.REQUEST_ACCEPTED)),
        connections_rated=Count("id", filter=Q(event_type=Type.CONNECTION_RATED)),
        connections_rated_useful=Count(
            "id", filter=Q(event_type=Type.CONNECTION_RATED, metadata__was_useful=True)
        ),
    )
