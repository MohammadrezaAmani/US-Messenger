import json
import logging
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from apps.chat.models import Attachment, ChatRoom, Message
from apps.chat.serializers import MessageSerializer
from apps.common.utils import (
    get_room_channel_group,
    get_user_channel_group,
    set_user_offline,
    set_user_online,
)

logger = logging.getLogger(__name__)


# Pydantic models for WebSocket message validation
class BaseWebSocketMessage(BaseModel):
    type: str


class JoinMessage(BaseWebSocketMessage):
    type: str = "join"


class LeaveMessage(BaseWebSocketMessage):
    type: str = "leave"


class MessageData(BaseModel):
    content: str
    reply_to: Optional[int] = None


class MessageMessage(BaseWebSocketMessage):
    type: str = "message"
    data: MessageData


class AttachmentData(BaseModel):
    message_id: Optional[int] = None
    filename: str
    file_url: str
    file_type: str
    file_size: int


class AttachmentMessage(BaseWebSocketMessage):
    type: str = "attachment"
    data: AttachmentData


class TypingMessage(BaseWebSocketMessage):
    type: str = "typing"
    data: Dict[str, Any] = {}


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat rooms."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_name = None
        self.user = None

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            # Get room_id from URL
            self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
            self.room_group_name = get_room_channel_group(self.room_id)

            # Get authenticated user
            self.user = self.scope.get("user")
            if not self.user or self.user.is_anonymous:
                await self.close(code=4001)  # Unauthorized
                return

            # Check room membership
            if not await self.is_room_member(self.user, self.room_id):
                await self.close(code=4003)  # Forbidden
                return

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()

            # Set user online
            await database_sync_to_async(set_user_online)(self.user.id, self.room_id)

            # Broadcast user joined
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_joined",
                    "user_id": self.user.id,
                    "username": self.user.get_full_name(),
                },
            )

        except Exception as e:
            logger.error(f"Chat consumer connect error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            if self.room_group_name:
                # Leave room group
                await self.channel_layer.group_discard(
                    self.room_group_name, self.channel_name
                )

                # Broadcast user left
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_left",
                        "user_id": self.user.id if self.user else None,
                        "username": (
                            self.user.get_full_name() if self.user else "Unknown"
                        ),
                    },
                )

            # Set user offline
            if self.user:
                await database_sync_to_async(set_user_offline)(self.user.id)

        except Exception as e:
            logger.error(f"Chat consumer disconnect error: {e}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)

            # Validate message type
            message_type = data.get("type")
            if not message_type:
                await self.send_error("Message type is required")
                return

            # Route to appropriate handler
            handlers = {
                "join": self.handle_join,
                "leave": self.handle_leave,
                "message": self.handle_message,
                "attachment": self.handle_attachment,
                "typing": self.handle_typing,
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
        except PydanticValidationError as e:
            await self.send_error(f"Validation error: {e}")
        except Exception as e:
            logger.error(f"Chat consumer receive error: {e}")
            await self.send_error("Internal server error")

    async def handle_join(self, data):
        """Handle join message."""
        try:
            message = JoinMessage(**data)
            # User is already joined during connect
            await self.send_success("Joined room")
        except PydanticValidationError as e:
            await self.send_error(f"Invalid join message: {e}")

    async def handle_leave(self, data):
        """Handle leave message."""
        try:
            message = LeaveMessage(**data)
            # User will leave during disconnect
            await self.send_success("Leaving room")
            await self.close(code=1000)
        except PydanticValidationError as e:
            await self.send_error(f"Invalid leave message: {e}")

    async def handle_message(self, data):
        """Handle text message."""
        try:
            message = MessageMessage(**data)

            # Create message in database
            db_message = await self.create_message(
                room_id=self.room_id,
                sender=self.user,
                content=message.data.content,
                reply_to=message.data.reply_to,
            )

            # Serialize message
            message_data = await self.serialize_message(db_message)

            # Broadcast to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message_data,
                },
            )

        except PydanticValidationError as e:
            await self.send_error(f"Invalid message: {e}")
        except Exception as e:
            logger.error(f"Handle message error: {e}")
            await self.send_error("Failed to send message")

    async def handle_attachment(self, data):
        """Handle attachment message."""
        try:
            message = AttachmentMessage(**data)

            # Create attachment message
            db_message = await self.create_attachment_message(
                room_id=self.room_id, sender=self.user, attachment_data=message.data
            )

            # Serialize message
            message_data = await self.serialize_message(db_message)

            # Broadcast to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_attachment",
                    "message": message_data,
                },
            )

        except PydanticValidationError as e:
            await self.send_error(f"Invalid attachment message: {e}")
        except Exception as e:
            logger.error(f"Handle attachment error: {e}")
            await self.send_error("Failed to send attachment")

    async def handle_typing(self, data):
        """Handle typing indicator."""
        try:
            message = TypingMessage(**data)

            # Broadcast typing status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_typing",
                    "user_id": self.user.id,
                    "username": self.user.get_full_name(),
                    "is_typing": message.data.get("is_typing", True),
                },
            )

        except PydanticValidationError as e:
            await self.send_error(f"Invalid typing message: {e}")

    # Event handlers for group messages
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "data": event["message"],
                }
            )
        )

    async def chat_attachment(self, event):
        """Send attachment message to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "attachment",
                    "data": event["message"],
                }
            )
        )

    async def user_joined(self, event):
        """Send user joined notification."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_joined",
                    "data": {
                        "user_id": event["user_id"],
                        "username": event["username"],
                    },
                }
            )
        )

    async def user_left(self, event):
        """Send user left notification."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_left",
                    "data": {
                        "user_id": event["user_id"],
                        "username": event["username"],
                    },
                }
            )
        )

    async def user_typing(self, event):
        """Send typing indicator."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "data": event,
                }
            )
        )

    async def user_presence_changed(self, event):
        """Send user presence change notification."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_presence_changed",
                    "data": event,
                }
            )
        )

    # Helper methods
    async def send_error(self, message):
        """Send error message."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "message": message,
                }
            )
        )

    async def send_success(self, message):
        """Send success message."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "success",
                    "message": message,
                }
            )
        )

    @database_sync_to_async
    def is_room_member(self, user, room_id):
        """Check if user is a member of the room."""
        return ChatRoom.objects.filter(
            id=room_id, participants=user, memberships__is_active=True
        ).exists()

    @database_sync_to_async
    def create_message(self, room_id, sender, content, reply_to=None):
        """Create a message in the database."""
        reply_to_obj = None
        if reply_to:
            try:
                reply_to_obj = Message.objects.get(id=reply_to)
            except Message.DoesNotExist:
                pass

        return Message.objects.create(
            room_id=room_id,
            sender=sender,
            content=content,
            reply_to=reply_to_obj,
        )

    @database_sync_to_async
    def create_attachment_message(self, room_id, sender, attachment_data):
        """Create an attachment message."""
        # Create message
        message = Message.objects.create(
            room_id=room_id,
            sender=sender,
            message_type="attachment",
        )

        # Create attachment (this would be done via REST API normally)
        # For now, we'll create a placeholder
        Attachment.objects.create(
            message=message,
            filename=attachment_data["filename"],
            file_type=attachment_data["file_type"],
            file_size=attachment_data["file_size"],
            mime_type="application/octet-stream",  # Placeholder
        )

        return message

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for WebSocket."""
        return MessageSerializer(message).data


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for user notifications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.notification_group = None

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            self.user = self.scope.get("user")
            if not self.user or self.user.is_anonymous:
                await self.close(code=4001)  # Unauthorized
                return

            self.notification_group = get_user_channel_group(self.user.id)

            # Join notification group
            await self.channel_layer.group_add(
                self.notification_group, self.channel_name
            )

            await self.accept()

        except Exception as e:
            logger.error(f"Notification consumer connect error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            if self.notification_group:
                await self.channel_layer.group_discard(
                    self.notification_group, self.channel_name
                )
        except Exception as e:
            logger.error(f"Notification consumer disconnect error: {e}")

    async def receive(self, text_data):
        """Handle incoming messages (ping/pong for keepalive)."""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "pong",
                            "timestamp": timezone.now().isoformat(),
                        }
                    )
                )
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON

    async def notification_message(self, event):
        """Send notification to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "data": event["notification"],
                }
            )
        )
