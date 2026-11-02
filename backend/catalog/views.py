from django.utils import timezone
from rest_framework import generics

from .models import Event, Interest, Role, Skill
from .serializers import CatalogEntrySerializer, EventSerializer


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = CatalogEntrySerializer
    pagination_class = None


class RoleListView(generics.ListAPIView):
    queryset = Role.objects.all()
    serializer_class = CatalogEntrySerializer
    pagination_class = None


class InterestListView(generics.ListAPIView):
    queryset = Interest.objects.all()
    serializer_class = CatalogEntrySerializer
    pagination_class = None


class EventListView(generics.ListAPIView):
    """Active events that have not ended yet, soonest first."""

    serializer_class = EventSerializer
    pagination_class = None

    def get_queryset(self):
        return Event.objects.filter(is_active=True, ends_at__gt=timezone.now())
