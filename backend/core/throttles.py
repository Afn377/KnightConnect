import hashlib

from django.core.exceptions import ImproperlyConfigured
from rest_framework import throttling
from rest_framework.settings import api_settings


class SettingsRateMixin:
    """Read the rate from the current settings on every request.

    DRF's throttles copy DEFAULT_THROTTLE_RATES at import time, which makes
    rates impossible to change per environment in tests.
    """

    def get_rate(self):
        try:
            return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
        except KeyError:
            raise ImproperlyConfigured(f"No throttle rate set for scope '{self.scope}'.")


class ScopedRateThrottle(SettingsRateMixin, throttling.ScopedRateThrottle):
    """Limit by user when signed in, otherwise by IP, using view.throttle_scope."""


class EmailRateThrottle(SettingsRateMixin, throttling.SimpleRateThrottle):
    """Limit requests that target the same email address, whoever sends them."""

    scope = "login_code_email"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        if not email:
            return None
        ident = hashlib.sha256(email.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
