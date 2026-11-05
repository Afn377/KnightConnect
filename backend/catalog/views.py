from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response

from core.throttles import ScopedRateThrottle

from .models import Event, Interest, Role, Skill
from .serializers import CatalogEntryCreateSerializer, CatalogEntrySerializer, EventSerializer
from .services import get_or_create_entry


class SearchableCatalogListView(generics.ListAPIView):
    """Alphabetical catalog list, narrowed by ``?search=`` (case-insensitive name match).

    Subclasses that set ``allow_create`` also accept POST {name}, which returns
    the existing entry with that name (200) or creates it (201).
    """

    model = None
    allow_create = False
    serializer_class = CatalogEntrySerializer
    pagination_class = None
    throttle_scope = "catalog_create"

    def get_throttles(self):
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def post(self, request):
        if not self.allow_create:
            return self.http_method_not_allowed(request)
        serializer = CatalogEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry, created = get_or_create_entry(self.model, serializer.validated_data["name"])
        return Response(
            CatalogEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def get_queryset(self):
        queryset = self.model.objects.all()
        if search := self.request.query_params.get("search", "").strip():
            queryset = queryset.filter(name__icontains=search)
        return queryset


class SkillListView(SearchableCatalogListView):
    model = Skill
    allow_create = True


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
