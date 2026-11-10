"""The pilot's two go/no-go measures, computed from what the app already records.

From the proposal:

1. At least 80% of active matching requests receive three or more qualified
   matches. A posted opportunity is a matching request. A qualified match is
   a student who passes every required filter, which is exactly what the
   matching engine returns, so the count is the size of the largest
   candidate list the owner was shown on the Matches page. Opportunities
   whose owner never opened Matches are reported as unmeasured rather than
   counted as failures.

2. At least 25% of active matching requests produce a useful connection:
   at least one accepted request on the post was rated useful by either side.
"""

from django.db.models import Count, Exists, OuterRef, Q

from connections.models import ConnectionFeedback, ConnectionRequest
from matching.models import MatchResult
from opportunities.models import Opportunity

QUALIFIED_MATCH_MINIMUM = 3
QUALIFIED_MATCH_TARGET = 0.80
USEFUL_CONNECTION_TARGET = 0.25


def _rate(part, whole):
    return round(part / whole, 3) if whole else None


def published_opportunities(start=None, end=None):
    """Posts that went live, optionally by local publication date (inclusive)."""
    posts = Opportunity.objects.exclude(status=Opportunity.Status.DRAFT)
    if start:
        posts = posts.filter(Q(published_at__date__gte=start) | Q(published_at__isnull=True, created_at__date__gte=start))
    if end:
        posts = posts.filter(Q(published_at__date__lte=end) | Q(published_at__isnull=True, created_at__date__lte=end))
    return posts


def pilot_metrics(start=None, end=None):
    posts = published_opportunities(start, end)

    batch_sizes = (
        MatchResult.objects.filter(direction=MatchResult.Direction.CANDIDATES_FOR_OPPORTUNITY)
        .values("opportunity", "batch_id")
        .annotate(size=Count("id"))
    )
    largest = {}
    for row in batch_sizes.filter(opportunity__in=posts):
        largest[row["opportunity"]] = max(largest.get(row["opportunity"], 0), row["size"])

    useful_feedback = ConnectionFeedback.objects.filter(
        connection_request__opportunity=OuterRef("pk"),
        connection_request__status=ConnectionRequest.Status.ACCEPTED,
        was_useful=True,
    )
    total = posts.count()
    with_useful = posts.filter(Exists(useful_feedback)).count()
    measured = len(largest)
    with_enough = sum(1 for size in largest.values() if size >= QUALIFIED_MATCH_MINIMUM)

    qualified_rate = _rate(with_enough, measured)
    useful_rate = _rate(with_useful, total)
    return {
        "opportunities": total,
        "qualified_matches": {
            "measured": measured,
            "unmeasured": total - measured,
            f"with_{QUALIFIED_MATCH_MINIMUM}_or_more": with_enough,
            "rate": qualified_rate,
            "target": QUALIFIED_MATCH_TARGET,
            "met": qualified_rate is not None and qualified_rate >= QUALIFIED_MATCH_TARGET,
        },
        "useful_connections": {
            "with_useful_connection": with_useful,
            "rate": useful_rate,
            "target": USEFUL_CONNECTION_TARGET,
            "met": useful_rate is not None and useful_rate >= USEFUL_CONNECTION_TARGET,
        },
    }

