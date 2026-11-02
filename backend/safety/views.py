from rest_framework import generics, status
from rest_framework.response import Response

from .models import Block
from .serializers import BlockCreateSerializer, BlockSerializer
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
