from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.throttles import ScopedRateThrottle

from .models import ConnectionRequest
from .serializers import ConnectionRequestSerializer, SendRequestSerializer
from .services import accept_request, decline_request, send_request


def requests_involving(user):
    return ConnectionRequest.objects.filter(Q(sender=user) | Q(recipient=user)).select_related(
        "opportunity", "opportunity_role__role", "sender", "recipient"
    ).prefetch_related("sender__contact_methods", "recipient__contact_methods")


class ConnectionRequestListView(generics.ListAPIView):
    """List my requests (GET) or send a join request or invite (POST).

    GET accepts ``box`` (incoming or outgoing) and ``status`` filters.
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
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by("-created_at")

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
