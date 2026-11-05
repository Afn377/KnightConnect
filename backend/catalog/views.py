from django.utils import timezone
from rest_framework import generics

from .models import Event, Interest, Role, Skill
from .serializers import CatalogEntrySerializer, EventSerializer


class SearchableCatalogListView(generics.ListAPIView):
    """Alphabetical catalog list, narrowed by ``?search=`` (case-insensitive name match)."""

    model = None
    serializer_class = CatalogEntrySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = self.model.objects.all()
        if search := self.request.query_params.get("search", "").strip():
            queryset = queryset.filter(name__icontains=search)
        return queryset


class SkillListView(SearchableCatalogListView):
    model = Skill


class RoleListView(SearchableCatalogListView):
    model = Role


class InterestListView(SearchableCatalogListView):
    model = Interest


class EventListView(generics.ListAPIView):
    """Active events that have not ended yet, soonest first."""

    serializer_class = EventSerializer
    pagination_class = None

    def get_queryset(self):
        return Event.objects.filter(is_active=True, ends_at__gt=timezone.now())
