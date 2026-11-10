from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDModel
from opportunities.models import Opportunity


class BlockQuerySet(models.QuerySet):
    def between(self, user_a, user_b):
        """Blocks in either direction between two users."""
        return self.filter(
            models.Q(blocker=user_a, blocked=user_b) | models.Q(blocker=user_b, blocked=user_a)
        )


class Block(models.Model):
    """A one-way block.

    Blocking hides both users from each other's browse and match results
    and prevents new connection requests in either direction.
    """

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = BlockQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="block_unique_pair"),
            models.CheckConstraint(
                condition=~models.Q(blocker=models.F("blocked")), name="block_not_self"
            ),
        ]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


class Report(UUIDModel, TimeStampedModel):
    """A report about a user (and optionally one of their opportunities) for moderators."""

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        HARASSMENT = "harassment", "Harassment or abuse"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        IMPERSONATION = "impersonation", "Impersonation or fake profile"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACTIONED = "actioned", "Action taken"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_made",
        help_text="Kept as null if the reporter deletes their account.",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_received"
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    moderator_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="report_status_created_idx")]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(reporter=models.F("reported_user")), name="report_not_self"
            ),
        ]

    def __str__(self):
        return f"{self.get_reason_display()} report on {self.reported_user} ({self.status})"
