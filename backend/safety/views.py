from rest_framework import generics, status
from rest_framework.response import Response

from core.throttles import ScopedRateThrottle

from .models import Block
from .serializers import BlockCreateSerializer, BlockSerializer, ReportSerializer
from .services import block_user


class BlockListView(generics.ListAPIView):
    """Users the signed-in user has blocked, most recent first (GET), or block someone (POST).

    Blocking hides the two users from each other and cancels pending
    requests between them. Blocking someone already blocked returns 200.
    """

    serializer_class = BlockSerializer
    pagination_class = None

    def get_queryset(self):
        return Block.objects.filter(blocker=self.request.user).select_related("blocked").order_by("-created_at")

    def post(self, request):
        serializer = BlockCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        block, created = block_user(request.user, serializer.validated_data["user"])
        return Response(
            BlockSerializer(block).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BlockDetailView(generics.DestroyAPIView):
    """Unblock a user, addressed by their user id."""

    lookup_field = "blocked_id"
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return Block.objects.filter(blocker=self.request.user)


class ReportCreateView(generics.CreateAPIView):
    """Report a user (optionally one of their opportunities) to the moderators."""

    serializer_class = ReportSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "report"
