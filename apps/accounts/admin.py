from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    """Admin configuration for User model."""

    # Fields to display in the list view
    list_display = (
        "email",
        "get_full_name",
        "is_online",
        "last_seen",
        "is_active",
        "is_staff",
        "date_joined",
    )

    # Fields to filter by
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_online",
        "date_joined",
        "last_seen",
    )

    # Fields to search by
    search_fields = ("email", "first_name", "last_name")

    # Ordering
    ordering = ("-date_joined",)

    # Fieldsets for the detail view
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "avatar", "bio")}),
        ("Status", {"fields": ("is_online", "last_seen")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Add fieldsets for creating new users
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    # Read-only fields
    readonly_fields = ("date_joined", "last_login", "last_seen")

    # Custom methods for list display
    def get_full_name(self, obj):
        return obj.get_full_name()

    get_full_name.short_description = "Full Name"

    # Actions
    actions = ["mark_online", "mark_offline"]

    def mark_online(self, request, queryset):
        """Mark selected users as online."""
        updated = queryset.update(is_online=True)
        self.message_user(
            request,
            f"{updated} user(s) marked as online.",
        )

    mark_online.short_description = "Mark selected users as online"

    def mark_offline(self, request, queryset):
        """Mark selected users as offline."""
        from django.utils import timezone

        updated = queryset.update(is_online=False, last_seen=timezone.now())
        self.message_user(
            request,
            f"{updated} user(s) marked as offline.",
        )

    mark_offline.short_description = "Mark selected users as offline"
