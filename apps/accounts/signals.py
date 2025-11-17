from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver


from .models import User


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Handle user login - set online status."""
    user.set_online()


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Handle user logout - set offline status."""
    user.set_offline()


@receiver(post_save, sender=User)
def user_status_changed(sender, instance, created, **kwargs):
    """Handle user status changes."""
    if not created and instance.pk:
        # Get the previous instance
        try:
            old_instance = User.objects.get(pk=instance.pk)
            status_changed = old_instance.is_online != instance.is_online

            if status_changed:
                channel_layer = get_channel_layer()

                # Notify user's rooms about status change
                from apps.chat.models import RoomMembership

                room_memberships = RoomMembership.objects.filter(
                    user=instance, is_active=True
                ).select_related("room")

                for membership in room_memberships:
                    room_group = f"chat_{membership.room.id}"
                    async_to_sync(channel_layer.group_send)(
                        room_group,
                        {
                            "type": "user_presence_changed",
                            "user_id": instance.id,
                            "username": instance.get_full_name(),
                            "is_online": instance.is_online,
                            "last_seen": (
                                instance.last_seen.isoformat()
                                if instance.last_seen
                                else None
                            ),
                        },
                    )

        except User.DoesNotExist:
            pass
