from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from social_api.api.v1.serializers.auth import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    TokenPairResponseSerializer,
    UserSerializer,
)


@extend_schema(
    tags=["auth"],
    summary="Log in",
    description="Exchange an email and password for an access/refresh token pair.",
    request=EmailTokenObtainPairSerializer,
    responses={200: TokenPairResponseSerializer},
    auth=[],
    examples=[
        OpenApiExample(
            "Credentials",
            value={"email": "ada@example.com", "password": "sup3rsecret"},
            request_only=True,
        )
    ],
)
class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=["auth"],
    summary="Register",
    description="Create an account. The password is hashed before it is stored.",
    auth=[],
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=["auth"],
    summary="Current user",
    description="Returns the user identified by the bearer token.",
)
class MeView(generics.RetrieveAPIView):
    """Protected route: requires a valid access token."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
