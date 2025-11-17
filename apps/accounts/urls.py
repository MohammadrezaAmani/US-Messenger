from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView

from apps.accounts.views import (
    ChangePasswordView,
    CustomTokenRefreshView,
    LoginView,
    ProfileView,
    RegisterView,
    user_search,
    websocket_user_info,
)

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", TokenBlacklistView.as_view(), name="logout"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    # Profile
    path("profile/", ProfileView.as_view(), name="profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    # Search
    path("search/", user_search, name="user_search"),
    # WebSocket
    path("ws-info/", websocket_user_info, name="websocket_user_info"),
]
