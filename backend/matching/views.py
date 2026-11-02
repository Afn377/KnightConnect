from django.conf import settings
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.exceptions import Conflict
from opportunities.queries import viewable_by

from .engine import rank_candidates, rank_opportunities
from .models import MatchResult
from .serializers import CandidateMatchSerializer, OpportunityMatchSerializer
from .services import record_matches


def match_response(batch_id, results, serializer_class, context):
    return Response(
        {
            "batch_id": batch_id,
            "results": serializer_class(results, many=True, context=context).data,
            "sparse": len(results) < settings.MATCHING_SPARSE_THRESHOLD,
        }
    )


class OpportunityMatchesView(generics.GenericAPIView):
    """Ranked, explained candidates for an opportunity, for its owner (Matches page)."""

    def get_queryset(self):
        return viewable_by(self.request.user)

    def get(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.owner_id != request.user.id:
            raise PermissionDenied("Only the owner can see matches for this opportunity.")
        if not opportunity.is_active:
            raise Conflict("This opportunity is no longer recruiting.")

        batch_id, results = record_matches(
            rank_candidates(opportunity),
            direction=MatchResult.Direction.CANDIDATES_FOR_OPPORTUNITY,
            viewer=request.user,
        )
        return match_response(batch_id, results, CandidateMatchSerializer, self.get_serializer_context())


class RecommendationsView(generics.GenericAPIView):
    """Ranked, explained opportunities for the signed-in student."""

    def get(self, request, *args, **kwargs):
        batch_id, results = record_matches(
            rank_opportunities(request.user),
            direction=MatchResult.Direction.OPPORTUNITIES_FOR_CANDIDATE,
            viewer=request.user,
        )
        return match_response(batch_id, results, OpportunityMatchSerializer, self.get_serializer_context())
