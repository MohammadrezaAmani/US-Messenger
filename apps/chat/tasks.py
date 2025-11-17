from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.chat.models import Attachment, ChatRoom, Message
from apps.notifications.tasks import send_bulk_notifications


@shared_task
def generate_daily_stats():
    """Generate daily statistics for chat service."""
    yesterday = timezone.now() - timedelta(days=1)
    today_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    stats = {
        "date": today_start.date(),
        "total_rooms": ChatRoom.objects.filter(is_active=True).count(),
        "total_messages": Message.objects.filter(
            created_at__gte=today_start, created_at__lt=today_end
        ).count(),
        "total_attachments": Attachment.objects.filter(
            created_at__gte=today_start, created_at__lt=today_end
        ).count(),
        "active_users": Message.objects.filter(
            created_at__gte=today_start, created_at__lt=today_end
        )
        .values("sender")
        .distinct()
        .count(),
    }

    # Log stats (in production, you might want to store these in a database)
    print(f"Daily Stats for {stats['date']}: {stats}")

    return stats


@shared_task
def cleanup_old_messages():
    """Clean up old messages (optional - for data retention compliance)."""
    # This would be configured based on your data retention policy
    # For now, just return a message
    return "Old message cleanup not implemented yet"


@shared_task
def process_attachment_thumbnail(attachment_id):
    """Process attachment thumbnail generation."""

    from django.conf import settings
    from PIL import Image

    from apps.chat.models import Attachment

    try:
        attachment = Attachment.objects.get(id=attachment_id)

        if attachment.file_type != "image":
            return f"Attachment {attachment_id} is not an image"

        # Generate thumbnail
        image_path = attachment.file.path
        thumbnail_path = attachment.file.path.replace(".", "_thumb.")

        with Image.open(image_path) as img:
            # Create thumbnail (max 200x200)
            img.thumbnail((200, 200))

            # Save thumbnail
            if attachment.filename.lower().endswith(
                ".jpg"
            ) or attachment.filename.lower().endswith(".jpeg"):
                img.save(thumbnail_path, "JPEG", quality=85)
            elif attachment.filename.lower().endswith(".png"):
                img.save(thumbnail_path, "PNG")
            else:
                img.save(thumbnail_path, "JPEG", quality=85)

        # Update attachment with thumbnail
        attachment.thumbnail = thumbnail_path.replace(settings.MEDIA_ROOT + "/", "")
        attachment.save(update_fields=["thumbnail"])

        return f"Thumbnail generated for attachment {attachment_id}"

    except Attachment.DoesNotExist:
        return f"Attachment {attachment_id} not found"
    except Exception as e:
        return f"Failed to generate thumbnail for attachment {attachment_id}: {str(e)}"


@shared_task
def notify_room_membership_change(room_id, user_id, action):
    """Notify room members about membership changes."""
    from apps.accounts.models import User
    from apps.chat.models import ChatRoom

    try:
        room = ChatRoom.objects.get(id=room_id)
        user = User.objects.get(id=user_id)

        # Get all room members except the user who joined/left
        member_ids = list(
            room.memberships.filter(is_active=True)
            .exclude(user=user)
            .values_list("user_id", flat=True)
        )

        if action == "joined":
            title = f"{user.get_full_name()} joined {room.name}"
            message = f"{user.get_full_name()} has joined the room."
        elif action == "left":
            title = f"{user.get_full_name()} left {room.name}"
            message = f"{user.get_full_name()} has left the room."
        else:
            return f"Unknown action: {action}"

        # Send notifications to all room members
        send_bulk_notifications.delay(
            recipient_ids=member_ids,
            notification_type="room_join" if action == "joined" else "room_leave",
            title=title,
            message=message,
            related_room_id=room_id,
            related_user_id=user_id,
        )

        return f"Membership change notification sent for room {room_id}"

    except (ChatRoom.DoesNotExist, User.DoesNotExist) as e:
        return f"Failed to send membership notification: {str(e)}"
