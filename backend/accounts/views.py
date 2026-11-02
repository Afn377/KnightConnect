from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
@ensure_csrf_cookie
def csrf(request):
    """Set the CSRF cookie and return the token for the frontend to echo back."""
    return JsonResponse({"csrf_token": get_token(request)})
