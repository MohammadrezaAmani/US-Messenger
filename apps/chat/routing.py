from django.urls import path

from apps.chat.consumers import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    path("chat/<int:room_id>/", ChatConsumer.as_asgi()),
    path("notifications/", NotificationConsumer.as_asgi()),
]
