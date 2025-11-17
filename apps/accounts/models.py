from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class UserManager(BaseUserManager):
    """Custom user manager that uses email instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """Custom User model extending Django's AbstractUser."""

    # Remove the default username field and use email as username
    username = None

    email = models.EmailField(
        _("email address"), unique=True, help_text=_("Required. A valid email address.")
    )

    # Profile fields
    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/", null=True, blank=True, help_text=_("User avatar image")
    )
    bio = models.TextField(max_length=500, blank=True, help_text=_("Short biography"))
    is_online = models.BooleanField(
        default=False, help_text=_("Whether the user is currently online")
    )
    last_seen = models.DateTimeField(
        null=True, blank=True, help_text=_("Last time the user was active")
    )

    # Additional fields for chat functionality
    # typing_in_room = models.ForeignKey(
    #     'chat.ChatRoom',
    #     null=True,
    #     blank=True,
    #     on_delete=models.SET_NULL,
    #     related_name='typing_users',
    #     help_text=_('Room where user is currently typing')
    # )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split("@")[0]

    def set_online(self):
        """Set user as online."""
        self.is_online = True
        self.last_seen = None
        self.save(update_fields=["is_online", "last_seen"])

    def set_offline(self):
        """Set user as offline."""
        from django.utils import timezone

        self.is_online = False
        self.last_seen = timezone.now()
        # self.typing_in_room = None
        self.save(update_fields=["is_online", "last_seen"])

    @property
    def avatar_url(self):
        """Get avatar URL or default."""
        if self.avatar:
            return self.avatar.url
        return None  # Frontend can handle default avatar
