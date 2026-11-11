from django.conf import settings
from django.db import models


class DoubleVerification(models.Model):
    compte = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="double_verification"
    )
    secret = models.CharField("clé secrète", max_length=64, blank=True)
    active = models.BooleanField("activée", default=False)
    date_activation = models.DateTimeField("activée le", null=True, blank=True)
    dernier_pas = models.BigIntegerField("dernier code utilisé", null=True, blank=True)

    class Meta:
        verbose_name = "double vérification"
        verbose_name_plural = "doubles vérifications"

    def __str__(self) -> str:
        return f"{self.compte} — {'activée' if self.active else 'non activée'}"
