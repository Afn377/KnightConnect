from rest_framework import generics

from .models import Block
from .serializers import BlockSerializer


class BlockListView(generics.ListAPIView):
    """Users the signed-in user has blocked, most recent first."""

    serializer_class = BlockSerializer
    pagination_class = None

    def get_queryset(self):
        return Block.objects.filter(blocker=self.request.user).select_related("blocked").order_by("-created_at")
