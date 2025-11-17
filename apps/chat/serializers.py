from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.chat.models import Attachment, ChatRoom, Message, RoomMembership
from apps.common.utils import get_time_ago


class RoomMembershipSerializer(serializers.ModelSerializer):
    """Serializer for room membership."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = RoomMembership
        fields = [
            "id",
            "user",
            "role",
            "joined_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "joined_at", "created_at", "updated_at"]


class ChatRoomListSerializer(serializers.ModelSerializer):
    """Serializer for chat room list view."""

    last_message = serializers.SerializerMethodField()
    participant_count = serializers.ReadOnlyField()
    avatar_url = serializers.ReadOnlyField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "name",
            "room_type",
            "description",
            "avatar_url",
            "is_active",
            "participant_count",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj):
        """Get last message info."""
        message = obj.last_message
        if message:
            return {
                "id": message.id,
                "content": message.content[:100],
                "sender": message.sender.get_full_name(),
                "created_at": message.created_at,
                "time_ago": get_time_ago(message.created_at),
                "has_attachments": message.has_attachments,
            }
        return None

    def get_unread_count(self, obj):
        """Get unread message count for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # This would be implemented with a proper unread tracking system
            # For now, return 0
            return 0
        return 0


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """Serializer for chat room detail view."""

    participants = UserSerializer(many=True, read_only=True)
    memberships = RoomMembershipSerializer(many=True, read_only=True)
    avatar_url = serializers.ReadOnlyField()
    participant_count = serializers.ReadOnlyField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "name",
            "room_type",
            "description",
            "avatar",
            "avatar_url",
            "is_active",
            "participant_count",
            "participants",
            "memberships",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "participant_count",
            "participants",
            "memberships",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat rooms."""

    participants = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of user IDs to add as participants",
    )
    name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ChatRoom
        fields = ["name", "room_type", "description", "avatar", "participants"]

    def validate(self, attrs):
        room_type = attrs.get("room_type", "private")
        participants = attrs.get("participants", [])

        if room_type == "private":
            if len(participants) != 1:
                raise serializers.ValidationError(
                    "Private rooms must have exactly one other participant."
                )
            # For private rooms, name is optional and will be auto-generated
        elif room_type == "group":
            if not attrs.get("name"):
                raise serializers.ValidationError("Group rooms must have a name.")
            if len(participants) < 1:
                raise serializers.ValidationError(
                    "Group rooms must have at least one participant."
                )

        return attrs

    def create(self, validated_data):
        participants = validated_data.pop("participants", [])
        room_type = validated_data.get("room_type", "private")

        # Generate name for private rooms if not provided
        if room_type == "private" and not validated_data.get("name"):
            # Get participant names for the room name
            from apps.accounts.models import User

            creator = self.context["request"].user
            other_user = User.objects.get(id=participants[0])

            # Create a name like "Private chat: User1 & User2"
            names = sorted(
                [
                    creator.get_full_name() or creator.email.split("@")[0],
                    other_user.get_full_name() or other_user.email.split("@")[0],
                ]
            )
            validated_data["name"] = f"Private chat: {names[0]} & {names[1]}"

        room = super().create(validated_data)

        # Add creator as owner
        RoomMembership.objects.create(
            user=self.context["request"].user, room=room, role="owner"
        )
        # Add creator to participants ManyToMany field
        room.participants.add(self.context["request"].user)

        # Add other participants
        for user_id in participants:
            RoomMembership.objects.create(user_id=user_id, room=room, role="member")
            # Add to participants ManyToMany field
            room.participants.add(user_id)

        return room


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for attachments."""

    file_url = serializers.ReadOnlyField()
    thumbnail_url = serializers.ReadOnlyField()
    file_size_mb = serializers.ReadOnlyField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "file",
            "filename",
            "file_type",
            "file_size",
            "file_size_mb",
            "mime_type",
            "file_url",
            "thumbnail_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "file_size",
            "file_size_mb",
            "mime_type",
            "file_url",
            "thumbnail_url",
            "created_at",
        ]


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages."""

    sender = UserSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    reply_to_content = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "room",
            "sender",
            "content",
            "message_type",
            "is_edited",
            "edited_at",
            "reply_to",
            "reply_to_content",
            "attachments",
            "has_attachments",
            "attachment_count",
            "time_ago",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "is_edited",
            "edited_at",
            "has_attachments",
            "attachment_count",
            "time_ago",
            "created_at",
            "updated_at",
        ]

    def get_reply_to_content(self, obj):
        """Get content of replied message."""
        if obj.reply_to:
            return {
                "id": obj.reply_to.id,
                "content": obj.reply_to.content[:100],
                "sender": obj.reply_to.sender.get_full_name(),
            }
        return None

    def get_time_ago(self, obj):
        """Get human readable time ago."""
        return get_time_ago(obj.created_at)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""

    class Meta:
        model = Message
        fields = ["content", "message_type", "reply_to"]

    def validate(self, attrs):
        message_type = attrs.get("message_type", "text")

        if message_type == "text" and not attrs.get("content", "").strip():
            raise serializers.ValidationError("Text messages must have content.")

        return attrs

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        validated_data["room_id"] = self.context["room_id"]
        return super().create(validated_data)


class AttachmentUploadSerializer(serializers.Serializer):
    """Serializer for attachment uploads."""

    file = serializers.FileField(required=True)
    message_id = serializers.IntegerField(required=False)

    def validate_file(self, value):
        """Validate uploaded file."""
        from apps.common.utils import (
            get_file_size_mb,
            validate_audio_file,
            validate_document_file,
            validate_image_file,
            validate_video_file,
        )

        # Determine file type
        filename = value.name.lower()
        if filename.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            file_type = "image"
            validator = validate_image_file
            max_size = 10
        elif filename.endswith((".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm")):
            file_type = "video"
            validator = validate_video_file
            max_size = 50
        elif filename.endswith((".mp3", ".wav", ".ogg", ".aac", ".m4a")):
            file_type = "audio"
            validator = validate_audio_file
            max_size = 20
        elif filename.endswith((".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt")):
            file_type = "document"
            validator = validate_document_file
            max_size = 10
        else:
            file_type = "file"
            validator = None
            max_size = 25

        # Validate file type
        if validator and not validator(value):
            raise serializers.ValidationError(f"Invalid {file_type} file type.")

        # Validate file size
        if get_file_size_mb(value.temporary_file_path()) > max_size:
            raise serializers.ValidationError(f"File size exceeds {max_size}MB limit.")

        # Store file type for later use
        self.context["file_type"] = file_type
        self.context["max_size"] = max_size

        return value
