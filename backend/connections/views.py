from rest_framework import generics, status
from rest_framework.response import Response

from core.throttles import ScopedRateThrottle

from .serializers import ConnectionRequestSerializer, SendRequestSerializer
from .services import send_request


class ConnectionRequestListView(generics.GenericAPIView):
    """Send a join request or invite (POST)."""

    serializer_class = ConnectionRequestSerializer
    throttle_scope = "connection_request"

    def get_throttles(self):
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def post(self, request):
        serializer = SendRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        connection_request = send_request(**serializer.validated_data)
        return Response(
            self.get_serializer(connection_request).data, status=status.HTTP_201_CREATED
        )
