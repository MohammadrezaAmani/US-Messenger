from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


@shared_task
def cleanup_expired_tokens():
    """Clean up expired JWT tokens from the blacklist."""
    # Remove tokens that expired more than 30 days ago
    cutoff_date = timezone.now() - timedelta(days=30)

    deleted_count, _ = OutstandingToken.objects.filter(
        expires_at__lt=cutoff_date
    ).delete()

    return f"Cleaned up {deleted_count} expired tokens"


@shared_task
def send_password_reset_email(user_id, reset_link):
    """Send password reset email to user."""
    from django.conf import settings
    from django.core.mail import send_mail

    from apps.accounts.models import User

    try:
        user = User.objects.get(id=user_id)
        subject = "Password Reset Request"
        message = f"""
        Hello {user.get_full_name()},
        
        You requested a password reset for your account.
        
        Please click the following link to reset your password:
        {reset_link}
        
        This link will expire in 24 hours.
        
        If you didn't request this password reset, please ignore this email.
        
        Best regards,
        Chat Service Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return f"Password reset email sent to {user.email}"

    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Failed to send password reset email: {str(e)}"
