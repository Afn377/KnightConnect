from datetime import timedelta

from django.utils import timezone

from .models import User

LAST_SEEN_INTERVAL = timedelta(minutes=5)


class LastSeenMiddleware:
    """Record when signed-in users were last active, writing at most every few minutes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = timezone.now()
            if user.last_seen_at is None or now - user.last_seen_at >= LAST_SEEN_INTERVAL:
                User.objects.filter(pk=user.pk).update(last_seen_at=now)
                user.last_seen_at = now
        return self.get_response(request)
