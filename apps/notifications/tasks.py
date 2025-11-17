from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.common.utils import get_user_channel_group
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


@shared_task
def cleanup_old_notifications():
    """Clean up old read notifications (older than 90 days)."""
    cutoff_date = timezone.now() - timedelta(days=90)

    deleted_count, _ = Notification.objects.filter(
        is_read=True, created_at__lt=cutoff_date
    ).delete()

    return f"Cleaned up {deleted_count} old notifications"


@shared_task
def send_notification_async(recipient_id, notification_type, title, message, **kwargs):
    """Send notification asynchronously."""
    from apps.notifications.models import Notification

    # Create notification
    notification = Notification.objects.create(
        recipient_id=recipient_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_room_id=kwargs.get("related_room_id"),
        related_message_id=kwargs.get("related_message_id"),
        related_user_id=kwargs.get("related_user_id"),
        extra_data=kwargs.get("extra_data"),
    )

    # Send WebSocket notification
    channel_layer = get_channel_layer()
    notification_group = get_user_channel_group(recipient_id)

    async_to_sync(channel_layer.group_send)(
        notification_group,
        {
            "type": "notification_message",
            "notification": NotificationSerializer(notification).data,
        },
    )

    return f"Notification sent to user {recipient_id}"


@shared_task
def send_bulk_notifications(recipient_ids, notification_type, title, message, **kwargs):
    """Send notifications to multiple users."""
    notifications = []

    for recipient_id in recipient_ids:
        notification = Notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_room_id=kwargs.get("related_room_id"),
            related_message_id=kwargs.get("related_message_id"),
            related_user_id=kwargs.get("related_user_id"),
            extra_data=kwargs.get("extra_data"),
        )
        notifications.append(notification)

    # Bulk create notifications
    created_notifications = Notification.objects.bulk_create(notifications)

    # Send WebSocket notifications
    channel_layer = get_channel_layer()

    for notification in created_notifications:
        notification_group = get_user_channel_group(notification.recipient_id)
        async_to_sync(channel_layer.group_send)(
            notification_group,
            {
                "type": "notification_message",
                "notification": NotificationSerializer(notification).data,
            },
        )

    return f"Bulk notifications sent to {len(recipient_ids)} users"
