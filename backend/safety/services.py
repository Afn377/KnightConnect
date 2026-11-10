from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from connections.models import ConnectionRequest

from .models import Block


@transaction.atomic
def block_user(blocker, blocked):
    """Block ``blocked`` and cancel pending requests between the two users.

    Returns (block, created).
    """
    block, created = Block.objects.get_or_create(blocker=blocker, blocked=blocked)
    now = timezone.now()
    ConnectionRequest.objects.filter(
        Q(sender=blocker, recipient=blocked) | Q(sender=blocked, recipient=blocker),
        status=ConnectionRequest.Status.PENDING,
    ).update(status=ConnectionRequest.Status.CANCELLED, responded_at=now, updated_at=now)
    return block, created
