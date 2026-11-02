from django.db.models import Count, Prefetch, Q

from accounts.models import User

from .models import Opportunity, OpportunityRole, OpportunitySkill


def with_details(queryset):
    """Load everything the opportunity serializer needs, with filled slots per role."""
    roles = (
        OpportunityRole.objects.select_related("role")
        .annotate(filled=Count("connection_requests", filter=Q(connection_requests__status="accepted")))
        .order_by("role__name")
    )
    skills = OpportunitySkill.objects.select_related("skill").order_by("skill__name")
    return queryset.select_related("owner", "event").prefetch_related(
        "interests",
        Prefetch("roles", queryset=roles),
        Prefetch("opportunity_skills", queryset=skills),
    )


def browsable_by(user):
    """Active opportunities whose owners are visible to ``user``."""
    return Opportunity.objects.active().filter(owner__in=User.objects.visible_to(user))
