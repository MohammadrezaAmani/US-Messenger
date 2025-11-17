import logging

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_string):
    """Get user from JWT token."""
    try:
        token = AccessToken(token_string)
        user_id = token.payload.get("user_id")
        if user_id:
            user = User.objects.get(id=user_id)
            return user
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        logger.warning(f"Invalid token or user not found: {e}")
    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom JWT authentication middleware for WebSocket connections.

    Expects the JWT token to be passed in the query string as 'token' parameter.
    Example: ws://example.com/chat/1/?token=your-jwt-token-here
    """

    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        token = None

        if query_string:
            # Parse query parameters
            params = dict(
                param.split("=", 1) for param in query_string.split("&") if "=" in param
            )
            token = params.get("token")

        if token:
            # Authenticate user
            user = await get_user_from_token(token)
            if user and not isinstance(user, AnonymousUser):
                # Set user online when connecting
                await database_sync_to_async(user.set_online)()
            else:
                user = AnonymousUser()
        else:
            user = AnonymousUser()

        # Add user to scope
        scope["user"] = user

        return await super().__call__(scope, receive, send)
