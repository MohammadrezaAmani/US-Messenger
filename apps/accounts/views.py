from django.contrib.auth import update_session_auth_hash
from django.db import models
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
    WebSocketUserSerializer,
)
from apps.common.exceptions import ValidationError


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    """User login endpoint."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Update last login
        user.set_online()

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            }
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """Change password endpoint."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        # Check old password
        if not user.check_password(serializer.validated_data["old_password"]):
            raise ValidationError({"old_password": "Wrong password."})

        # Set new password
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Update session auth hash to prevent logout
        update_session_auth_hash(request, user)

        return Response({"message": "Password updated successfully."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_search(request):
    """Search for users by email or name."""
    query = request.query_params.get("q", "").strip()

    if not query:
        return Response({"results": []})

    # Search by email or name
    users = User.objects.filter(
        models.Q(email__icontains=query)
        | models.Q(first_name__icontains=query)
        | models.Q(last_name__icontains=query)
    ).exclude(id=request.user.id)[:10]  # Limit to 10 results, exclude current user

    serializer = UserSerializer(users, many=True)
    return Response({"results": serializer.data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def websocket_user_info(request):
    """Get current user info for WebSocket authentication."""
    serializer = WebSocketUserSerializer(request.user)
    return Response(serializer.data)


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view with user data."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Add user data to response
            user = request.user
            response.data["user"] = UserSerializer(user).data

        return response
