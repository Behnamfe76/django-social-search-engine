"""Route-level authentication middleware.

DRF permission classes only cover DRF views. This middleware puts a gate in front
of whole path prefixes, so a route is protected regardless of what serves it.

A request is rejected with 401 JSON when its path starts with one of
``settings.AUTH_PROTECTED_PREFIXES`` and none of ``settings.AUTH_EXEMPT_PREFIXES``
(exempt wins), and it carries no valid credentials.

It runs after ``AuthenticationMiddleware``, so a session-authenticated user (the
admin, say) passes without a token. Otherwise the Bearer token is validated and
``request.user`` is populated, which means downstream non-DRF views see the user
too.
"""

import json

from django.conf import settings
from django.http import HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken


class JWTRouteAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.authenticator = JWTAuthentication()

    def __call__(self, request):
        if self.is_protected(request.path):
            error = self.authenticate(request)
            if error is not None:
                return self.unauthorized(error)
        return self.get_response(request)

    def is_protected(self, path):
        protected = tuple(getattr(settings, "AUTH_PROTECTED_PREFIXES", ()))
        exempt = tuple(getattr(settings, "AUTH_EXEMPT_PREFIXES", ()))
        if not protected or not path.startswith(protected):
            return False
        return not (exempt and path.startswith(exempt))

    def authenticate(self, request):
        """Return None when the request may proceed, else a reason string."""
        try:
            result = self.authenticator.authenticate(request)
        except (AuthenticationFailed, InvalidToken) as exc:
            return str(exc.detail if hasattr(exc, "detail") else exc)

        if result is not None:
            request.user, request.auth = result
            return None

        # No Bearer header: fall back to whatever AuthenticationMiddleware resolved.
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return None
        return "Authentication credentials were not provided."

    def unauthorized(self, detail):
        response = HttpResponse(
            json.dumps({"detail": detail}),
            content_type="application/json",
            status=401,
        )
        response["WWW-Authenticate"] = 'Bearer realm="api"'
        return response
