import uuid
from decimal import Decimal

from django.db import transaction

from analytics.models import FunnelEvent

from .models import MatchResult


@transaction.atomic
def record_matches(matches, *, direction, viewer):
    """Persist one ranking run and log each result as shown to ``viewer``.

    Returns (batch_id, match results in rank order).
    """
    batch_id = uuid.uuid4()
    results = MatchResult.objects.bulk_create(
        MatchResult(
            batch_id=batch_id,
            direction=direction,
            opportunity=match.opportunity,
            candidate=match.candidate,
            rank=rank,
            score=Decimal(str(match.score)),
            explanation_factors=[factor.as_dict() for factor in match.factors],
        )
        for rank, match in enumerate(matches, start=1)
    )
    FunnelEvent.objects.bulk_create(
        FunnelEvent(
            event_type=FunnelEvent.Type.RECOMMENDATION_SHOWN,
            user=viewer,
            opportunity=result.opportunity,
            match_result=result,
            metadata={"direction": direction, "rank": result.rank},
        )
        for result in results
    )
    return batch_id, results
