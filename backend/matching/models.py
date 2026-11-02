import uuid

from django.conf import settings
from django.db import models

from opportunities.models import Opportunity


class MatchResult(models.Model):
    """One ranked pairing produced by a recommendation run.

    Rankings are computed on request and every result is persisted so the
    pilot can audit what was shown, in what order, and why. All rows from a
    single run share a ``batch_id``.
    """

    class Direction(models.TextChoices):
        CANDIDATES_FOR_OPPORTUNITY = "candidates", "Candidates for an opportunity"
        OPPORTUNITIES_FOR_CANDIDATE = "opportunities", "Opportunities for a student"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_id = models.UUIDField(db_index=True)
    direction = models.CharField(max_length=15, choices=Direction.choices)
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="match_results"
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_results"
    )
    rank = models.PositiveSmallIntegerField()
    score = models.DecimalField(max_digits=6, decimal_places=3)
    explanation_factors = models.JSONField(
        default=list,
        help_text='Ordered list of factors, e.g. [{"factor": "skill", "label": "Backend experience", "weight": 0.3}].',
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["batch_id", "rank"]
        indexes = [
            models.Index(fields=["opportunity", "-generated_at"], name="match_opp_generated_idx"),
            models.Index(fields=["candidate", "-generated_at"], name="match_cand_generated_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["batch_id", "opportunity", "candidate"], name="match_unique_pair_per_batch"
            ),
            models.UniqueConstraint(fields=["batch_id", "rank"], name="match_unique_rank_per_batch"),
        ]

    def __str__(self):
        return f"#{self.rank} {self.candidate} <-> {self.opportunity} ({self.score})"
