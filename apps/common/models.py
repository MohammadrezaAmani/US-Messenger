from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """Base model with common fields for all models."""

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Set created_at only on first save
        if not self.pk:
            self.created_at = timezone.now()
        return super().save(*args, **kwargs)
