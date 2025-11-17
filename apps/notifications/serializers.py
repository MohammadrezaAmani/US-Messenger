from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.chat.serializers import ChatRoomListSerializer, MessageSerializer
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""

    time_since = serializers.ReadOnlyField()
    related_user_data = serializers.SerializerMethodField()
    related_room_data = serializers.SerializerMethodField()
    related_message_data = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "read_at",
            "time_since",
            "related_user_data",
            "related_room_data",
            "related_message_data",
            "extra_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "time_since",
            "related_user_data",
            "related_room_data",
            "related_message_data",
            "created_at",
            "updated_at",
        ]

    def get_related_user_data(self, obj):
        """Get related user data."""
        if obj.related_user:
            return UserSerializer(obj.related_user).data
        return None

    def get_related_room_data(self, obj):
        """Get related room data."""
        if obj.related_room:
            return ChatRoomListSerializer(obj.related_room).data
        return None

    def get_related_message_data(self, obj):
        """Get related message data."""
        if obj.related_message:
            return MessageSerializer(obj.related_message).data
        return None


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for notification lists."""

    time_since = serializers.ReadOnlyField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "time_since",
            "created_at",
        ]
        read_only_fields = ["id", "time_since", "created_at"]


class MarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""

    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of notification IDs to mark as read",
    )
