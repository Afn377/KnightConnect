from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.throttles import ScopedRateThrottle

from .models import ConnectionRequest
from .serializers import ConnectionFeedbackSerializer, ConnectionRequestSerializer, SendRequestSerializer
from .services import accept_request, cancel_request, decline_request, rate_connection, send_request


def requests_involving(user):
    return ConnectionRequest.objects.filter(Q(sender=user) | Q(recipient=user)).select_related(
        "opportunity", "opportunity_role__role", "sender", "recipient"
    ).prefetch_related(
        "sender__contact_methods",
        "recipient__contact_methods",
        "feedback",
        "opportunity__opportunity_skills__skill",
        "opportunity__roles__role",
        "opportunity__interests",
        "sender__user_skills__skill",
        "sender__preferred_roles",
        "sender__interests",
        "sender__interested_events",
        "recipient__user_skills__skill",
        "recipient__preferred_roles",
        "recipient__interests",
        "recipient__interested_events",
    )


LIVE = [ConnectionRequest.Status.PENDING, ConnectionRequest.Status.ACCEPTED]


def request_tab_counts(user):
    """Counts for the Sent, Received, and History tabs on the Request page."""
    mine = ConnectionRequest.objects.filter(Q(sender=user) | Q(recipient=user))
    return {
        "sent": mine.filter(sender=user, status__in=LIVE).count(),
        "received": mine.filter(recipient=user, status__in=LIVE).count(),
        "history": mine.exclude(status__in=LIVE).count(),
    }


class ConnectionRequestListView(generics.ListAPIView):
    """List my requests (GET) or send a join request or invite (POST).

    GET accepts ``box`` (incoming or outgoing), ``status`` (one or more,
    comma-separated), and ``opportunity`` filters, and adds counts for the
    Sent, Received, and History tabs.
    """

    serializer_class = ConnectionRequestSerializer
    throttle_scope = "connection_request"

    def get_throttles(self):
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        user = self.request.user
        queryset = requests_involving(user)
        box = self.request.query_params.get("box")
        if box == "incoming":
            queryset = queryset.filter(recipient=user)
        elif box == "outgoing":
            queryset = queryset.filter(sender=user)
        elif box:
            raise ValidationError({"box": ["Use 'incoming' or 'outgoing'."]})
        if status_filter := self.request.query_params.get("status"):
            queryset = queryset.filter(status__in=status_filter.split(","))
        if opportunity := self.request.query_params.get("opportunity"):
            queryset = queryset.filter(opportunity_id=opportunity)
        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["counts"] = request_tab_counts(request.user)
        return response

    def post(self, request):
        serializer = SendRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        connection_request = send_request(**serializer.validated_data)
        return Response(
            self.get_serializer(connection_request).data, status=status.HTTP_201_CREATED
        )


class ConnectionRequestDetailView(generics.RetrieveAPIView):
    """One request, visible only to its two participants."""

    serializer_class = ConnectionRequestSerializer

    def get_queryset(self):
        return requests_involving(self.request.user)


class RespondToRequestView(generics.GenericAPIView):
    """Base for actions one participant takes on a request."""

    serializer_class = ConnectionRequestSerializer
    allowed_party = "recipient"

    def get_queryset(self):
        return requests_involving(self.request.user)

    def get_request_for_action(self):
        connection_request = self.get_object()
        if getattr(connection_request, f"{self.allowed_party}_id") != self.request.user.id:
            raise PermissionDenied(f"Only the {self.allowed_party} can do this.")
        return connection_request

    def respond(self, connection_request):
        connection_request = self.get_queryset().get(pk=connection_request.pk)
        return Response(self.get_serializer(connection_request).data)


class AcceptRequestView(RespondToRequestView):
    def post(self, request, *args, **kwargs):
        connection_request = accept_request(self.get_request_for_action(), actor=request.user)
        return self.respond(connection_request)


class DeclineRequestView(RespondToRequestView):
    def post(self, request, *args, **kwargs):
        connection_request = decline_request(self.get_request_for_action(), actor=request.user)
        return self.respond(connection_request)


class CancelRequestView(RespondToRequestView):
    allowed_party = "sender"

    def post(self, request, *args, **kwargs):
        connection_request = cancel_request(self.get_request_for_action(), actor=request.user)
        return self.respond(connection_request)


class ConnectionFeedbackView(generics.GenericAPIView):
    """Either participant rates whether an accepted connection helped (once each)."""

    serializer_class = ConnectionFeedbackSerializer

    def get_queryset(self):
        return requests_involving(self.request.user)

    def post(self, request, *args, **kwargs):
        connection_request = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = rate_connection(connection_request, user=request.user, **serializer.validated_data)
        return Response(self.get_serializer(feedback).data, status=status.HTTP_201_CREATED)
