from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification model."""

    list_display = (
        "id",
        "recipient",
        "notification_type",
        "title",
        "is_read",
        "created_at",
        "time_since",
    )
    list_filter = ("notification_type", "is_read", "created_at", "read_at")
    search_fields = ("recipient__email", "title", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "read_at", "time_since", "id")

    fieldsets = (
        (
            None,
            {"fields": ("id", "recipient", "notification_type", "title", "message")},
        ),
        ("Status", {"fields": ("is_read", "read_at")}),
        (
            "Related Objects",
            {"fields": ("related_room", "related_message", "related_user")},
        ),
        ("Extra Data", {"fields": ("extra_data",)}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at", "time_since"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "recipient", "related_room", "related_message", "related_user"
            )
        )

    # Actions
    actions = ["mark_as_read", "mark_as_unread"]

    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = queryset.update(is_read=True)
        self.message_user(
            request,
            f"{updated} notification(s) marked as read.",
        )

    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread."""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(
            request,
            f"{updated} notification(s) marked as unread.",
        )

    mark_as_unread.short_description = "Mark selected notifications as unread"
