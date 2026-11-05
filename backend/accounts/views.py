from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import EmailRateThrottle, ScopedRateThrottle

from .avatars import process_avatar
from .deletion import restore_account, schedule_account_deletion
from .login_codes import InvalidLoginCode, issue_login_code, verify_login_code
from .models import ContactMethod, User
from .serializers import (
    ContactMethodSerializer,
    MeSerializer,
    PublicProfileSerializer,
    RequestCodeSerializer,
    SessionUserSerializer,
    VerifyCodeSerializer,
)


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

        restored = restore_account(user)
        login(request, user)
        return Response(
            {"user": SessionUserSerializer(user).data, "created": created, "restored": restored}
        )


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """The signed-in user's own profile.

    DELETE schedules the account for deletion after a grace period and
    signs the user out; signing in again before then restores it.
    """

    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_object(self):
        return self.request.user

    def delete(self, request):
        user = request.user
        schedule_account_deletion(user)
        logout(request)
        return Response(
            {
                "detail": "Your account is scheduled for deletion. Sign in again before then to restore it.",
                "deletion_scheduled_for": user.deletion_scheduled_for,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ContactMethodListView(generics.ListCreateAPIView):
    """The signed-in user's contact methods, revealed to others only after an accepted connection."""

    serializer_class = ContactMethodSerializer
    pagination_class = None

    def get_queryset(self):
        return ContactMethod.objects.filter(user=self.request.user)


class ContactMethodDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    serializer_class = ContactMethodSerializer
    http_method_names = ["patch", "delete", "options"]

    def get_queryset(self):
        return ContactMethod.objects.filter(user=self.request.user)


class PublicProfileView(generics.RetrieveAPIView):
    """Another student's public profile. Blocked, disabled, and deleting accounts return 404."""

    serializer_class = PublicProfileSerializer

    def get_queryset(self):
        return User.objects.visible_to(self.request.user).prefetch_related(
            "preferred_roles", "interests", "interested_events", "event_interests__event", "user_skills__skill"
        )


class AvatarView(APIView):
    """Upload (POST, multipart field ``image``) the signed-in user's profile picture."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("image")
        if upload is None:
            raise ValidationError({"image": ["Choose an image to upload."]})
        try:
            content = process_avatar(upload)
        except DjangoValidationError as error:
            raise ValidationError({"image": error.messages})

        user = request.user
        previous = user.avatar.name if user.avatar else None
        user.avatar.save("avatar.jpg", content, save=True)
        if previous:
            user.avatar.storage.delete(previous)
        return Response({"avatar_url": MeSerializer(user, context={"request": request}).data["avatar_url"]})
