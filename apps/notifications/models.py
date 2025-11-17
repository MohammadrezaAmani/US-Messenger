from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Notification(BaseModel):
    """Notification model for user notifications."""

    NOTIFICATION_TYPES = [
        ("message", "New Message"),
        ("mention", "Mention"),
        ("room_invite", "Room Invitation"),
        ("room_join", "User Joined Room"),
        ("room_leave", "User Left Room"),
        ("system", "System Notification"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default="message"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Related objects (optional)
    related_room = models.ForeignKey(
        "chat.ChatRoom",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    related_message = models.ForeignKey(
        "chat.Message",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
    )

    # Additional data as JSON
    extra_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"Notification for {self.recipient}: {self.title}"

    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def mark_as_unread(self):
        """Mark notification as unread."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=["is_read", "read_at"])

    @property
    def time_since(self):
        """Get human readable time since notification."""
        from apps.common.utils import get_time_ago

        return get_time_ago(self.created_at)
