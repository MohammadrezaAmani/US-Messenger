from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chat.models import Attachment, ChatRoom, Message, RoomMembership
from apps.chat.serializers import (
    AttachmentSerializer,
    AttachmentUploadSerializer,
    ChatRoomCreateSerializer,
    ChatRoomDetailSerializer,
    ChatRoomListSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    RoomMembershipSerializer,
)
from apps.common.exceptions import NotFound, PermissionDenied
from apps.common.mixins import BaseModelViewSet


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination for messages."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class ChatRoomViewSet(BaseModelViewSet):
    """ViewSet for chat rooms."""

    queryset = ChatRoom.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "create":
            return ChatRoomCreateSerializer
        elif self.action in ["retrieve", "update", "partial_update"]:
            return ChatRoomDetailSerializer
        return ChatRoomListSerializer

    def get_queryset(self):
        """Filter rooms for current user."""
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()

        return (
            self.queryset.filter(participants=user)
            .prefetch_related("participants", "memberships", "memberships__user")
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        """List chat rooms."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """Join a chat room."""
        room = self.get_object()

        # Check if user is already a member
        membership, created = RoomMembership.objects.get_or_create(
            user=request.user, room=room, defaults={"role": "member"}
        )

        if not created and not membership.is_active:
            membership.is_active = True
            membership.save()

        serializer = RoomMembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        """Leave a chat room."""
        room = self.get_object()

        try:
            membership = RoomMembership.objects.get(
                user=request.user, room=room, is_active=True
            )
            membership.is_active = False
            membership.save()

            return Response({"message": "Successfully left the room."})
        except RoomMembership.DoesNotExist:
            raise NotFound("You are not a member of this room.")

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get messages for a room."""
        room = self.get_object()

        # Check if user is a member
        if not room.participants.filter(id=request.user.id).exists():
            raise PermissionDenied("You are not a member of this room.")

        messages = (
            Message.objects.filter(room=room)
            .select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("attachments")
        )

        # Search functionality
        search = request.query_params.get("search")
        if search:
            messages = messages.filter(
                Q(content__icontains=search)
                | Q(sender__first_name__icontains=search)
                | Q(sender__last_name__icontains=search)
                | Q(sender__email__icontains=search)
            )

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        messages = messages.order_by(ordering)

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class MessageViewSet(BaseModelViewSet):
    """ViewSet for messages."""

    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter messages for current user."""
        user = self.request.user
        return (
            self.queryset.filter(
                room__participants=user,
                room__memberships__is_active=True,
                room__is_active=True,
            )
            .select_related("sender", "room", "reply_to", "reply_to__sender")
            .prefetch_related("attachments")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        """Validate room membership before creating message."""
        room_id = self.request.data.get("room_id")
        if not room_id:
            raise serializers.ValidationError({"room": "Room ID is required."})

        try:
            room = ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            raise NotFound("Room not found.")

        # Check membership
        if not room.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You are not a member of this room.")

        serializer.save(room=room, sender=self.request.user)

    @action(detail=True, methods=["patch"])
    def edit(self, request, pk=None):
        """Edit a message."""
        message = self.get_object()

        # Check if user is the sender
        if message.sender != request.user:
            raise PermissionDenied("You can only edit your own messages.")

        # Check if message is not too old (e.g., 15 minutes)
        from datetime import timedelta

        from django.utils import timezone

        if timezone.now() - message.created_at > timedelta(minutes=15):
            raise PermissionDenied("Messages can only be edited within 15 minutes.")

        serializer = self.get_serializer(message, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(is_edited=True, edited_at=timezone.now())

        return Response(serializer.data)

    @action(detail=True, methods=["delete"])
    def soft_delete(self, request, pk=None):
        """Soft delete a message (mark as deleted)."""
        message = self.get_object()

        if message.sender != request.user:
            # Check if user is admin/owner
            membership = RoomMembership.objects.filter(
                user=request.user,
                room=message.room,
                role__in=["admin", "owner"],
                is_active=True,
            ).first()

            if not membership:
                raise PermissionDenied("You can only delete your own messages.")

        # Instead of deleting, we could mark as deleted
        # For now, we'll actually delete
        message.delete()

        return Response({"message": "Message deleted successfully."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_attachment(request):
    """Upload attachment for a message."""
    serializer = AttachmentUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    file = serializer.validated_data["file"]
    message_id = serializer.validated_data.get("message_id")

    # Get or create message
    if message_id:
        try:
            message = Message.objects.get(id=message_id)
            # Check if user can attach to this message
            if message.sender != request.user:
                raise PermissionDenied(
                    "You can only attach files to your own messages."
                )
        except Message.DoesNotExist:
            raise NotFound("Message not found.")
    else:
        # Create a new message for the attachment
        message = Message.objects.create(
            sender=request.user,
            room_id=request.data.get("room_id"),
            message_type="attachment",
        )

    # Create attachment
    attachment = Attachment.objects.create(
        message=message,
        file=file,
        filename=file.name,
        file_type=serializer.context["file_type"],
        file_size=file.size,
        mime_type=file.content_type,
    )

    # Generate thumbnail for images if needed
    if attachment.file_type == "image":
        # This would be handled by a Celery task
        pass

    serializer = AttachmentSerializer(attachment)
    return Response(
        {"attachment": serializer.data, "message_id": message.id},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def room_members(request, room_id):
    """Get room members."""
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        raise NotFound("Room not found.")

    # Check membership
    if not room.participants.filter(id=request.user.id).exists():
        raise PermissionDenied("You are not a member of this room.")

    memberships = RoomMembership.objects.filter(
        room=room, is_active=True
    ).select_related("user")

    serializer = RoomMembershipSerializer(memberships, many=True)
    return Response(serializer.data)
