from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import EmailRateThrottle, ScopedRateThrottle

from .login_codes import issue_login_code
from .serializers import RequestCodeSerializer


@require_GET
@ensure_csrf_cookie
def csrf(request):
    """Set the CSRF cookie and return the token for the frontend to echo back."""
    return JsonResponse({"csrf_token": get_token(request)})


class RequestCodeView(APIView):
    """Email a one-time sign-in code to a Rutgers address.

    The response is identical whether or not an account exists, so the
    endpoint cannot be used to discover who has signed up.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, EmailRateThrottle]
    throttle_scope = "login_code"

    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue_login_code(serializer.validated_data["email"])
        return Response(
            {"detail": "A sign-in code has been sent to your email."},
            status=status.HTTP_202_ACCEPTED,
        )
