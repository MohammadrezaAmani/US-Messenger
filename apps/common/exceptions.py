import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework.
    Provides consistent error responses and logging.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Log the error
        logger.warning(
            f"API Error: {exc.__class__.__name__}: {str(exc)}",
            extra={
                "status_code": response.status_code,
                "view": context.get("view", {})
                .get("__class__", {})
                .get("__name__", "Unknown"),
                "request_method": context.get("request", {}).method,
                "request_path": context.get("request", {}).path,
            },
        )

        # Customize error response format
        custom_response_data = {
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "details": response.data if hasattr(response, "data") else None,
            }
        }

        response.data = custom_response_data

    return response


class ValidationError(APIException):
    """Custom validation error with detailed field information."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error occurred."
    default_code = "validation_error"


class AuthenticationError(APIException):
    """Custom authentication error."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were not provided or are invalid."
    default_code = "authentication_error"


class PermissionDenied(APIException):
    """Custom permission denied error."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class NotFound(APIException):
    """Custom not found error."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class ConflictError(APIException):
    """Custom conflict error for duplicate resources."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflict occurred with the current state of the resource."
    default_code = "conflict_error"


class ServiceUnavailable(APIException):
    """Custom service unavailable error."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable. Please try again later."
    default_code = "service_unavailable"
