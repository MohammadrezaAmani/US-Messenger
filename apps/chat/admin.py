from django.contrib import admin
from django.utils.html import format_html

from .models import Attachment, ChatRoom, Message, RoomMembership


class RoomMembershipInline(admin.TabularInline):
    """Inline admin for room memberships."""

    model = RoomMembership
    extra = 0
    readonly_fields = ("joined_at",)
    fields = ("user", "role", "is_active", "joined_at")


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin configuration for ChatRoom model."""

    list_display = (
        "id",
        "name",
        "room_type",
        "participant_count",
        "is_active",
        "created_by",
        "created_at",
        "last_message_preview",
    )
    list_filter = ("room_type", "is_active", "created_at", "updated_at")
    search_fields = ("name", "description", "created_by__email")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "id")
    inlines = [RoomMembershipInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "room_type", "description")}),
        ("Media", {"fields": ("avatar",)}),
        ("Status", {"fields": ("is_active", "created_by")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def last_message_preview(self, obj):
        """Show preview of last message."""
        last_msg = obj.last_message
        if last_msg:
            sender = last_msg.sender.get_full_name() or last_msg.sender.email
            content = (
                last_msg.content[:50] + "..."
                if len(last_msg.content) > 50
                else last_msg.content
            )
            return f"{sender}: {content}"
        return "No messages"

    last_message_preview.short_description = "Last Message"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("created_by")


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for RoomMembership model."""

    list_display = ("id", "user", "room", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active", "joined_at", "room__room_type")
    search_fields = ("user__email", "user__first_name", "user__last_name", "room__name")
    ordering = ("-joined_at",)
    readonly_fields = ("joined_at", "id")

    fieldsets = (
        (None, {"fields": ("id", "user", "room", "role", "is_active")}),
        ("Timestamps", {"fields": ("joined_at",), "classes": ("collapse",)}),
    )


class AttachmentInline(admin.TabularInline):
    """Inline admin for message attachments."""

    model = Attachment
    extra = 0
    readonly_fields = ("file_url", "thumbnail_url", "file_size_mb")
    fields = (
        "file",
        "filename",
        "file_type",
        "file_size_mb",
        "file_url",
        "thumbnail_url",
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin configuration for Message model."""

    list_display = (
        "id",
        "room",
        "sender",
        "content_preview",
        "message_type",
        "has_attachments",
        "is_edited",
        "created_at",
    )
    list_filter = ("message_type", "is_edited", "created_at", "room__room_type")
    search_fields = ("content", "sender__email", "room__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "edited_at", "id")
    inlines = [AttachmentInline]

    fieldsets = (
        (None, {"fields": ("id", "room", "sender", "content", "message_type")}),
        ("Status", {"fields": ("is_edited", "edited_at")}),
        ("Reply", {"fields": ("reply_to",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def content_preview(self, obj):
        """Show preview of message content."""
        if obj.content:
            return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
        return "[Attachment only]" if obj.has_attachments else "[Empty]"

    content_preview.short_description = "Content"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("room", "sender")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for Attachment model."""

    list_display = (
        "id",
        "message",
        "filename",
        "file_type",
        "file_size_mb",
        "created_at",
        "file_url_link",
    )
    list_filter = ("file_type", "created_at", "message__room__room_type")
    search_fields = ("filename", "message__content", "message__sender__email")
    ordering = ("-created_at",)
    readonly_fields = (
        "file_url",
        "thumbnail_url",
        "file_size_mb",
        "created_at",
        "updated_at",
        "id",
    )

    fieldsets = (
        (None, {"fields": ("id", "message", "file", "filename")}),
        ("File Info", {"fields": ("file_type", "file_size", "mime_type")}),
        ("Thumbnail", {"fields": ("thumbnail",)}),
        ("Links", {"fields": ("file_url", "thumbnail_url"), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def file_url_link(self, obj):
        """Show clickable link to file."""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">View File</a>', obj.file.url
            )
        return "No file"

    file_url_link.short_description = "File Link"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("message__room", "message__sender")
        )
