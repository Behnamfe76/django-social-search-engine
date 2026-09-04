"""Shared test helpers."""

from rest_framework_simplejwt.tokens import RefreshToken


def access_token(user):
    return str(RefreshToken.for_user(user).access_token)


def authenticate(client, user):
    """Attach a real Bearer token to an APIClient.

    ``force_authenticate`` is not enough here: JWTRouteAuthMiddleware runs before
    the view and would reject the request before DRF ever sees it.
    """
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token(user)}")
    return client
