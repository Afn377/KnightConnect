from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import ScopedRateThrottle

from .pilot import pilot_metrics
from .reports import funnel_counts
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


class FunnelReportView(APIView):
    """Staff-only funnel counts: shown, viewed, requested, accepted, rated, rated useful.

    Optional ``start`` and ``end`` (YYYY-MM-DD, inclusive, campus time).
    """

    permission_classes = [IsAdminUser]

    def _date(self, name):
        raw = self.request.query_params.get(name)
        if not raw:
            return None
        value = parse_date(raw) if len(raw) == 10 else None
        if value is None:
            raise ValidationError({name: ["Use the YYYY-MM-DD format."]})
        return value

    def get(self, request):
        start, end = self._date("start"), self._date("end")
        if start and end and start > end:
            raise ValidationError({"end": ["End must not be before start."]})
        return Response({"start": start, "end": end, "funnel": funnel_counts(start, end)})


class PilotMetricsView(FunnelReportView):
    """Staff-only pilot success measures: qualified-match rate and useful-connection rate.

    Takes the same optional ``start`` and ``end`` as the funnel report.
    """

    def get(self, request):
        start, end = self._date("start"), self._date("end")
        if start and end and start > end:
            raise ValidationError({"end": ["End must not be before start."]})
        return Response({"start": start, "end": end, "pilot": pilot_metrics(start, end)})
