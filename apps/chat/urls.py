from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.chat.views import (
    ChatRoomViewSet,
    MessageViewSet,
    room_members,
    upload_attachment,
)

app_name = "chat"

router = DefaultRouter()
router.register(r"rooms", ChatRoomViewSet)
router.register(r"messages", MessageViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("upload-attachment/", upload_attachment, name="upload_attachment"),
    path("rooms/<int:room_id>/members/", room_members, name="room_members"),
]
