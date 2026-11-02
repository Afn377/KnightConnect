from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import ScopedRateThrottle

from .serializers import TrackEventSerializer


class TrackEventView(APIView):
    """Record a funnel step observed by the frontend (opportunity or recommendation viewed)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "analytics"

    def post(self, request):
        serializer = TrackEventSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
