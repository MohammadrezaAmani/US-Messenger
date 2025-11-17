from django.conf import settings
from django.db import connection
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

app_name = "common"


@api_view(["GET"])
def health_check(request):
    """Health check endpoint."""
    # Check database connection
    db_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_status = "error"

    return Response(
        {
            "status": "ok",
            "database": db_status,
            "version": "1.0.0",
            "environment": "development" if settings.DEBUG else "production",
        }
    )


urlpatterns = [
    path("", health_check, name="health_check"),
]
