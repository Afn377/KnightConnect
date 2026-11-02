from rest_framework.authentication import SessionAuthentication as DRFSessionAuthentication


class SessionAuthentication(DRFSessionAuthentication):
    """Session authentication that answers unauthenticated requests with 401.

    DRF's version returns 403 because it sends no WWW-Authenticate header,
    which makes "not signed in" indistinguishable from "not allowed" for the
    frontend.
    """

    def authenticate_header(self, request):
        return "Session"
