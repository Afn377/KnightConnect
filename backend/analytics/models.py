from django.conf import settings
from django.db import models

from connections.models import ConnectionRequest
from matching.models import MatchResult
from opportunities.models import Opportunity


class FunnelEvent(models.Model):
    """An append-only record of a step in the discovery funnel.

    Related rows use SET_NULL so the funnel stays countable after a user
    deletes their account or an opportunity is removed; deleting a user
    therefore anonymizes rather than erases their events.
    """

    class Type(models.TextChoices):
        RECOMMENDATION_SHOWN = "recommendation_shown", "Recommendation shown"
        RECOMMENDATION_VIEWED = "recommendation_viewed", "Recommendation viewed"
        OPPORTUNITY_VIEWED = "opportunity_viewed", "Opportunity viewed"
        REQUEST_SENT = "request_sent", "Request sent"
        REQUEST_ACCEPTED = "request_accepted", "Request accepted"
        REQUEST_DECLINED = "request_declined", "Request declined"
        REQUEST_CANCELLED = "request_cancelled", "Request cancelled"
        CONNECTION_RATED = "connection_rated", "Connection rated"
        OPPORTUNITY_CREATED = "opportunity_created", "Opportunity created"
        OPPORTUNITY_CLOSED = "opportunity_closed", "Opportunity closed"

    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=32, choices=Type.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="funnel_events",
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name="funnel_events"
    )
    match_result = models.ForeignKey(
        MatchResult, on_delete=models.SET_NULL, null=True, blank=True, related_name="funnel_events"
    )
    connection_request = models.ForeignKey(
        ConnectionRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="funnel_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["event_type", "occurred_at"], name="funnel_type_occurred_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} at {self.occurred_at:%Y-%m-%d %H:%M}"

    @classmethod
    def record(cls, event_type, *, user=None, opportunity=None, match_result=None, connection_request=None, **metadata):
        return cls.objects.create(
            event_type=event_type,
            user=user,
            opportunity=opportunity,
            match_result=match_result,
            connection_request=connection_request,
            metadata=metadata,
        )
