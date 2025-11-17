import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional

import redis
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# Redis Connection
def get_redis_connection():
    """Get Redis connection for custom operations."""
    return redis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True
    )


# Cache utilities
def cache_key(*args, **kwargs):
    """Generate a cache key from arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    return hashlib.md5(":".join(key_parts).encode()).hexdigest()


def cached(timeout=300):
    """Decorator to cache function results."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = cache_key(func.__name__, *args, **kwargs)
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(key, result, timeout)
            return result

        return wrapper

    return decorator


# Time utilities
def get_time_ago(dt: datetime) -> str:
    """Get human readable time ago string."""
    now = timezone.now()
    diff = now - dt if dt else timedelta()

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string."""
    if dt is None:
        return ""
    return dt.strftime(format_str)


# File utilities
def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension."""
    extension = get_file_extension(original_filename)
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{extension}"


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(file_path) / (1024 * 1024)


def validate_file_type(filename: str, allowed_types: list) -> bool:
    """Validate file type against allowed types."""
    extension = get_file_extension(filename)
    return extension in allowed_types


def validate_file_size(file_path: str, max_size_mb: float) -> bool:
    """Validate file size."""
    return get_file_size_mb(file_path) <= max_size_mb


# Presence tracking utilities
def get_user_presence_key(user_id: int) -> str:
    """Generate Redis key for user presence."""
    return f"presence:user:{user_id}"


def get_room_presence_key(room_id: int) -> str:
    """Generate Redis key for room presence."""
    return f"presence:room:{room_id}"


def set_user_online(user_id: int, room_id: Optional[int] = None) -> None:
    """Set user as online."""
    redis_conn = get_redis_connection()
    key = get_user_presence_key(user_id)

    # Set user online with expiration
    redis_conn.setex(key, 60, "online")  # 60 seconds timeout

    if room_id:
        room_key = get_room_presence_key(room_id)
        redis_conn.sadd(room_key, user_id)
        redis_conn.expire(room_key, 60)


def set_user_offline(user_id: int) -> None:
    """Set user as offline."""
    redis_conn = get_redis_connection()
    key = get_user_presence_key(user_id)
    redis_conn.delete(key)

    # Remove from all rooms
    pattern = "presence:room:*"
    for room_key in redis_conn.scan_iter(pattern):
        redis_conn.srem(room_key, user_id)


def get_online_users_in_room(room_id: int) -> list:
    """Get list of online users in a room."""
    redis_conn = get_redis_connection()
    room_key = get_room_presence_key(room_id)
    return [int(uid) for uid in redis_conn.smembers(room_key)]


def is_user_online(user_id: int) -> bool:
    """Check if user is online."""
    redis_conn = get_redis_connection()
    key = get_user_presence_key(user_id)
    return redis_conn.exists(key)


# WebSocket utilities
def get_user_channel_group(user_id: int) -> str:
    """Get channel group name for user notifications."""
    return f"notifications_{user_id}"


def get_room_channel_group(room_id: int) -> str:
    """Get channel group name for room messages."""
    return f"chat_{room_id}"


# Pagination utilities
def get_pagination_info(queryset, page_size: int = 20, page: int = 1) -> Dict[str, Any]:
    """Get pagination information for a queryset."""
    total_count = queryset.count()
    total_pages = (total_count + page_size - 1) // page_size

    return {
        "total_count": total_count,
        "total_pages": total_pages,
        "page_size": page_size,
        "current_page": page,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


# Validation utilities
def validate_image_file(file) -> bool:
    """Validate if file is a valid image."""
    allowed_types = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    return validate_file_type(file.name, allowed_types)


def validate_video_file(file) -> bool:
    """Validate if file is a valid video."""
    allowed_types = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]
    return validate_file_type(file.name, allowed_types)


def validate_audio_file(file) -> bool:
    """Validate if file is a valid audio file."""
    allowed_types = [".mp3", ".wav", ".ogg", ".aac", ".m4a"]
    return validate_file_type(file.name, allowed_types)


def validate_document_file(file) -> bool:
    """Validate if file is a valid document."""
    allowed_types = [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"]
    return validate_file_type(file.name, allowed_types)
