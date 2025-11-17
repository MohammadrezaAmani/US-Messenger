from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import NotificationViewSet, create_notification

app_name = "notifications"

router = DefaultRouter()
router.register(r"", NotificationViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("create/", create_notification, name="create_notification"),
]
