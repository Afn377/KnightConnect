from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from analytics.models import FunnelEvent
from catalog.models import Event
from core.exceptions import Conflict

from .models import Opportunity
from .queries import browsable_by, viewable_by, with_details
from .serializers import OpportunitySerializer
from .services import close_opportunity, delete_opportunity, publish_opportunity


class OpportunityListView(generics.ListCreateAPIView):
    """Browse active opportunities (GET) or post a new one (POST).

    Query parameters: ``q`` (searches title, description, role, and skill
    names), ``event``, ``role``, ``skill``, and ``interest`` (slugs),
    ``type``, ``commitment``, ``location``, and ``status`` (the event's: upcoming or ongoing).
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
        if interest := params.get("interest"):
            queryset = queryset.filter(interests__slug=interest)
        if commitment := params.get("commitment"):
            queryset = queryset.filter(commitment=commitment)
        if location := params.get("location"):
            queryset = queryset.filter(location_type=location)
        if event_status := params.get("status"):
            queryset = queryset.filter(event__in=Event.objects.with_status(event_status))

        return with_details(queryset.distinct().order_by("-created_at"))

    def perform_create(self, serializer):
        opportunity = serializer.save()
        if opportunity.status == Opportunity.Status.OPEN:
            FunnelEvent.record(
                FunnelEvent.Type.OPPORTUNITY_CREATED, user=self.request.user, opportunity=opportunity
            )


class OpportunityDetailView(generics.RetrieveUpdateAPIView):
    """View an opportunity (GET); as its owner, edit it while it is open (PATCH) or delete it (DELETE)."""

    serializer_class = OpportunitySerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return with_details(viewable_by(self.request.user))

    def update(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.owner_id != request.user.id:
            raise PermissionDenied("Only the owner can edit this opportunity.")
        if opportunity.status != Opportunity.Status.DRAFT and not opportunity.is_active:
            raise Conflict("Closed or expired opportunities can't be edited.")
        return super().update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.owner_id != request.user.id:
            raise PermissionDenied("Only the owner can delete this opportunity.")
        delete_opportunity(opportunity)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OpportunityCloseView(generics.GenericAPIView):
    """Let the owner stop recruiting before the opportunity expires."""

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        return viewable_by(self.request.user)

    def post(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.owner_id != request.user.id:
            raise PermissionDenied("Only the owner can close this opportunity.")
        if opportunity.status != Opportunity.Status.OPEN:
            raise Conflict("This opportunity is already closed.")

        close_opportunity(opportunity, Opportunity.CloseReason.OWNER_CLOSED, actor=request.user)
        opportunity = with_details(Opportunity.objects.filter(pk=opportunity.pk)).get()
        return Response(self.get_serializer(opportunity).data)


class MyOpportunitiesView(generics.ListAPIView):
    """The signed-in user's own opportunities in any state. Optional ``status`` filter."""

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        queryset = Opportunity.objects.filter(owner=self.request.user)
        if status_filter := self.request.query_params.get("status"):
            queryset = queryset.filter(status=status_filter)
        return with_details(queryset.order_by("-created_at"))


class OpportunityPublishView(generics.GenericAPIView):
    """Publish a draft once it has everything a post needs."""

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        return viewable_by(self.request.user)

    def post(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.owner_id != request.user.id:
            raise PermissionDenied("Only the owner can publish this opportunity.")
        if opportunity.status != Opportunity.Status.DRAFT:
            raise Conflict("Only drafts can be published.")
        try:
            publish_opportunity(opportunity, actor=request.user)
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict)
        opportunity = with_details(Opportunity.objects.filter(pk=opportunity.pk)).get()
        return Response(self.get_serializer(opportunity).data)


class OpportunityReopenView(generics.GenericAPIView):
    """Reopen recruiting on a post its owner closed early, before the deadline."""

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        return viewable_by(self.request.user)

    def post(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.owner_id != request.user.id:
            raise PermissionDenied("Only the owner can reopen this opportunity.")
        if not (
            opportunity.status == Opportunity.Status.CLOSED
            and opportunity.close_reason == Opportunity.CloseReason.OWNER_CLOSED
        ):
            raise Conflict("Only posts you closed early can be reopened.")
        if opportunity.expires_at <= timezone.now():
            raise Conflict("The recruiting deadline has passed.")
        opportunity.reopen()
        opportunity = with_details(Opportunity.objects.filter(pk=opportunity.pk)).get()
        return Response(self.get_serializer(opportunity).data)
