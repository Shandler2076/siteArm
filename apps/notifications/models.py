from django.conf import settings
from django.db import models


class Notification(models.Model):
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField("message", max_length=300)
    lien = models.CharField("lien", max_length=200, blank=True)
    lue = models.BooleanField("lue", default=False)
    date = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-date", "-pk"]

    def __str__(self) -> str:
        return self.message
