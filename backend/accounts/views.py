from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import EmailRateThrottle, ScopedRateThrottle

from .login_codes import InvalidLoginCode, issue_login_code, verify_login_code
from .models import User
from .serializers import MeSerializer, RequestCodeSerializer, SessionUserSerializer, VerifyCodeSerializer


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


class VerifyCodeView(APIView):
    """Exchange a valid one-time code for a session, creating the account on first sign-in."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login_verify"

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            verify_login_code(email, serializer.validated_data["code"])
        except InvalidLoginCode as error:
            raise ValidationError({"code": [str(error)]})

        user = User.objects.filter(email=email).first()
        created = user is None
        if created:
            user = User.objects.create_user(email)
        if not user.is_active:
            raise PermissionDenied("This account has been disabled.")

        login(request, user)
        return Response({"user": SessionUserSerializer(user).data, "created": created})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """The signed-in user's own profile."""

    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
