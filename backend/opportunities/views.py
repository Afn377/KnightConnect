from django.db.models import Q
from rest_framework import generics

from analytics.models import FunnelEvent

from .queries import browsable_by, with_details
from .serializers import OpportunitySerializer


class OpportunityListView(generics.ListCreateAPIView):
    """Browse active opportunities (GET) or post a new one (POST).

    Query parameters: ``q`` (searches title, description, role, and skill
    names), ``event``, ``role``, and ``skill`` (slugs), and ``type``.
    """

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        queryset = browsable_by(self.request.user)
        params = self.request.query_params

        if q := params.get("q", "").strip():
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(roles__role__name__icontains=q)
                | Q(opportunity_skills__skill__name__icontains=q)
            )
        if event := params.get("event"):
            queryset = queryset.filter(event__slug=event)
        if role := params.get("role"):
            queryset = queryset.filter(roles__role__slug=role)
        if skill := params.get("skill"):
            queryset = queryset.filter(opportunity_skills__skill__slug=skill)
        if opportunity_type := params.get("type"):
            queryset = queryset.filter(opportunity_type=opportunity_type)

        return with_details(queryset.distinct().order_by("-created_at"))

    def perform_create(self, serializer):
        opportunity = serializer.save()
        FunnelEvent.record(
            FunnelEvent.Type.OPPORTUNITY_CREATED, user=self.request.user, opportunity=opportunity
        )
