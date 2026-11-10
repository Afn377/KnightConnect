from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel, UUIDModel
from opportunities.models import Opportunity, OpportunityRole


class ConnectionRequest(UUIDModel, TimeStampedModel):
    """A request to connect two students around one opportunity.

    Requests flow in both directions through the same accept/decline cycle:
    a student can ask to join an opportunity (JOIN), or an owner can invite
    a recommended candidate (INVITE). Contact methods are revealed to both
    sides only once the request is ACCEPTED.
    """

    class Kind(models.TextChoices):
        JOIN = "join", "Join request"
        INVITE = "invite", "Invite"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="connection_requests"
    )
    opportunity_role = models.ForeignKey(
        OpportunityRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="connection_requests",
        help_text="The open role the candidate would fill.",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_requests"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_requests"
    )
    message = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "status"], name="connreq_recipient_status_idx"),
            models.Index(fields=["sender", "status"], name="connreq_sender_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(sender=models.F("recipient")),
                name="connreq_not_self",
            ),
            models.UniqueConstraint(
                fields=["opportunity", "sender", "recipient"],
                condition=models.Q(status="pending"),
                name="connreq_one_pending_per_pair",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.sender} -> {self.recipient} ({self.status})"

    @property
    def candidate(self):
        """The student who would join the team."""
        return self.sender if self.kind == self.Kind.JOIN else self.recipient

    def clean(self):
        super().clean()
        if not (self.opportunity_id and self.sender_id and self.recipient_id):
            return
        owner_id = self.opportunity.owner_id
        if self.kind == self.Kind.JOIN and self.recipient_id != owner_id:
            raise ValidationError("Join requests must be sent to the opportunity owner.")
        if self.kind == self.Kind.INVITE and self.sender_id != owner_id:
            raise ValidationError("Only the opportunity owner can send invites.")
        if self.opportunity_role_id and self.opportunity_role.opportunity_id != self.opportunity_id:
            raise ValidationError({"opportunity_role": "Role does not belong to this opportunity."})


class ConnectionFeedback(TimeStampedModel):
    """A participant's in-app rating of whether an accepted connection helped.

    Drives the pilot's "useful connection" success metric.
    """

    connection_request = models.ForeignKey(
        ConnectionRequest, on_delete=models.CASCADE, related_name="feedback"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="connection_feedback"
    )
    was_useful = models.BooleanField(
        help_text="Did this connection help form or advance a team?",
    )
    comment = models.TextField(max_length=1000, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection_request", "user"], name="connfeedback_one_per_user"
            ),
        ]

    def __str__(self):
        return f"{self.user} on {self.connection_request_id}: {'useful' if self.was_useful else 'not useful'}"

    def clean(self):
        super().clean()
        if not (self.connection_request_id and self.user_id):
            return
        request = self.connection_request
        if request.status != ConnectionRequest.Status.ACCEPTED:
            raise ValidationError("Feedback can only be left on accepted connections.")
        if self.user_id not in (request.sender_id, request.recipient_id):
            raise ValidationError("Only participants can leave feedback on a connection.")
