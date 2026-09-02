from django.conf import settings
from django.db import models


class SavedSearch(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_searches'
    )
    title = models.CharField(max_length=150)
    criteria = models.JSONField(help_text="Stored search filters, radius, budget, amenities preferences")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
