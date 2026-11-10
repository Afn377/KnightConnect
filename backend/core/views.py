import hmac

from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .maintenance import run_maintenance


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Liveness and database connectivity check for uptime monitoring."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        database = "unavailable"

    status_code = 200 if database == "ok" else 503
    return Response({"status": "ok" if status_code == 200 else "degraded", "database": database}, status=status_code)


class CronSecretPermission(AllowAny):
    """Allow only callers presenting the configured CRON_SECRET as a bearer token."""

    message = "Invalid or missing cron secret."

    def has_permission(self, request, view):
        secret = settings.CRON_SECRET
        if not secret:
            return False
        header = request.headers.get("Authorization", "")
        return hmac.compare_digest(header.encode(), f"Bearer {secret}".encode())


class MaintenanceView(APIView):
    """Periodic housekeeping, triggered by Vercel Cron (GET) or manually (POST).

    Expires opportunities past their deadline (and their pending requests),
    permanently deletes accounts whose recovery period has ended, and
    purges old login codes.
    """

    authentication_classes = []
    permission_classes = [CronSecretPermission]

    def get(self, request):
        return Response(run_maintenance())

    def post(self, request):
        return Response(run_maintenance())
