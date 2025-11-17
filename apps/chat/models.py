from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import (
    get_file_size_mb,
    validate_audio_file,
    validate_document_file,
    validate_image_file,
    validate_video_file,
)


class ChatRoom(BaseModel):
    """Chat room model supporting both private and group chats."""

    ROOM_TYPES = [
        ("private", "Private"),
        ("group", "Group"),
    ]

    name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Room name (required for groups, auto-generated for private)",
    )
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default="private")
    description = models.TextField(
        max_length=500, blank=True, help_text="Room description", null=True
    )
    avatar = models.ImageField(
        upload_to="room_avatars/", null=True, blank=True, help_text="Room avatar image"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the room is active"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_rooms"
    )

    # For private rooms (1-on-1 chats)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="RoomMembership",
        related_name="chat_rooms",
        help_text="Room participants",
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["room_type", "is_active"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        if self.room_type == "private":
            try:
                participants = list(self.participants.all()[:2])
                if len(participants) == 2:
                    return f"Private chat: {participants[0]} & {participants[1]}"
                return f"Private chat: {participants[0] if participants else 'Unknown'}"
            except (RecursionError, AttributeError, ValueError):
                # Handle case where participants aren't fully loaded yet
                return f"Private chat: {self.name or 'Unknown'}"
        return self.name

    def clean(self):
        if self.room_type == "group" and not self.name:
            raise ValidationError("Group rooms must have a name.")

        # Only validate participant count if the room has been saved (has pk)
        if self.pk and self.room_type == "private":
            try:
                if self.participants.count() != 2:
                    raise ValidationError(
                        "Private rooms must have exactly 2 participants."
                    )
            except (AttributeError, ValueError):
                # Skip validation if participants aren't accessible yet
                pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def last_message(self):
        """Get the last message in this room."""
        return self.messages.order_by("-created_at").first()

    @property
    def participant_count(self):
        """Get the number of participants."""
        return self.participants.count()

    @property
    def avatar_url(self):
        """Get avatar URL."""
        if self.avatar:
            return self.avatar.url
        return None


class RoomMembership(BaseModel):
    """Membership model for room participants."""

    ROLE_CHOICES = [
        ("member", "Member"),
        ("admin", "Admin"),
        ("owner", "Owner"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_memberships",
    )
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True, help_text="Whether the membership is active"
    )

    class Meta:
        unique_together = ["user", "room"]
        ordering = ["-joined_at"]
        indexes = [
            models.Index(fields=["room", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} in {self.room} ({self.role})"

    def clean(self):
        # Ensure only one owner per room
        if self.role == "owner":
            existing_owner = RoomMembership.objects.filter(
                room=self.room, role="owner", is_active=True
            ).exclude(pk=self.pk)
            if existing_owner.exists():
                raise ValidationError("A room can only have one owner.")


class Message(BaseModel):
    """Message model with support for text and attachments."""

    MESSAGE_TYPES = [
        ("text", "Text"),
        ("attachment", "Attachment"),
        ("system", "System"),
    ]

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField(
        blank=True, help_text="Message content (optional for attachment messages)"
    )
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default="text"
    )
    is_edited = models.BooleanField(
        default=False, help_text="Whether the message has been edited"
    )
    edited_at = models.DateTimeField(
        null=True, blank=True, help_text="When the message was last edited"
    )
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
        help_text="Message this is replying to",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["message_type"]),
        ]

    def __str__(self):
        return f"Message by {self.sender} in {self.room}: {self.content[:50]}"

    def clean(self):
        if self.message_type == "text" and not self.content.strip():
            raise ValidationError("Text messages must have content.")

    @property
    def has_attachments(self):
        """Check if message has attachments."""
        return self.attachments.exists()

    @property
    def attachment_count(self):
        """Get number of attachments."""
        return self.attachments.count()


class Attachment(BaseModel):
    """Attachment model for files, images, videos, etc."""

    ATTACHMENT_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("document", "Document"),
        ("file", "File"),
    ]

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="chat_attachments/", help_text="Uploaded file")
    filename = models.CharField(max_length=255, help_text="Original filename")
    file_type = models.CharField(
        max_length=20, choices=ATTACHMENT_TYPES, help_text="Type of attachment"
    )
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, help_text="MIME type of the file")
    thumbnail = models.ImageField(
        upload_to="attachment_thumbnails/",
        null=True,
        blank=True,
        help_text="Thumbnail for images/videos",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["message"]),
            models.Index(fields=["file_type"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.file_type})"

    def clean(self):
        # Validate file type and size
        max_sizes = {
            "image": 10,  # 10MB
            "video": 50,  # 50MB
            "audio": 20,  # 20MB
            "document": 10,  # 10MB
            "file": 25,  # 25MB
        }

        max_size = max_sizes.get(self.file_type, 10)
        if get_file_size_mb(self.file.path) > max_size:
            raise ValidationError(
                f"File size exceeds {max_size}MB limit for {self.file_type} files."
            )

        # Validate file type
        validators = {
            "image": validate_image_file,
            "video": validate_video_file,
            "audio": validate_audio_file,
            "document": validate_document_file,
        }

        validator = validators.get(self.file_type)
        if validator and hasattr(self.file, "name") and not validator(self.file):
            raise ValidationError(f"Invalid {self.file_type} file type.")

    @property
    def file_url(self):
        """Get file URL."""
        return self.file.url

    @property
    def thumbnail_url(self):
        """Get thumbnail URL."""
        if self.thumbnail:
            return self.thumbnail.url
        return None

    @property
    def file_size_mb(self):
        """Get file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)
