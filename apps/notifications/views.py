from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import BaseModelViewSet
from apps.notifications.models import Notification
from apps.notifications.serializers import (
    MarkReadSerializer,
    NotificationListSerializer,
    NotificationSerializer,
)


class NotificationViewSet(BaseModelViewSet):
    """ViewSet for user notifications."""

    queryset = Notification.objects.all()  # This will be filtered in get_queryset
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter notifications for current user."""
        return Notification.objects.filter(recipient=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.mark_as_read()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_unread(self, request, pk=None):
        """Mark a single notification as unread."""
        notification = self.get_object()
        notification.mark_as_unread()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"message": "All notifications marked as read."})

    @action(detail=False, methods=["post"])
    def bulk_mark_read(self, request):
        """Mark multiple notifications as read."""
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data["notification_ids"]
        updated_count = (
            self.get_queryset()
            .filter(id__in=notification_ids, is_read=False)
            .update(is_read=True)
        )

        return Response(
            {
                "message": f"{updated_count} notifications marked as read.",
                "updated_count": updated_count,
            }
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_notification(request):
    """
    Create a notification (internal API for other apps).
    This endpoint should be protected and only called by internal services.
    """
    # This would be used by Celery tasks or other internal services
    # to create notifications

    serializer = NotificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    notification = serializer.save()

    # Send WebSocket notification
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    from apps.common.utils import get_user_channel_group

    channel_layer = get_channel_layer()
    notification_group = get_user_channel_group(notification.recipient_id)

    async_to_sync(channel_layer.group_send)(
        notification_group,
        {
            "type": "notification_message",
            "notification": NotificationSerializer(notification).data,
        },
    )

    return Response(serializer.data, status=status.HTTP_201_CREATED)
