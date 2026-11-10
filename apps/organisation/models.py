"""Organisation territoriale : Région → Circuit → Paroisse.

On ne supprime jamais une unité : on la ferme, pour que l'historique des membres reste vrai.
"""

import datetime

from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

MESSAGE_SUPPRESSION = "On ne supprime pas : utilisez « fermer »."


class Fermable(models.Model):
    active = models.BooleanField("active", default=True)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_fermeture = models.DateField("date de fermeture", null=True, blank=True)

    class Meta:
        abstract = True

    def fermer(self, date: datetime.date | None = None) -> None:
        self.active = False
        self.date_fermeture = date or timezone.localdate()
        self.save(update_fields=["active", "date_fermeture"])

    def rouvrir(self) -> None:
        self.active = True
        self.date_fermeture = None
        self.save(update_fields=["active", "date_fermeture"])

    def delete(self, *args, **kwargs):
        raise PermissionDenied(MESSAGE_SUPPRESSION)


class Region(Fermable):
    code = models.CharField(
        "code",
        max_length=2,
        unique=True,
        validators=[RegexValidator(r"^(0[1-9]|[1-9][0-9])$", "Code à 2 chiffres, de 01 à 99.")],
        help_text="Code à 2 chiffres, utilisé dans les matricules. Jamais réattribué.",
    )
    nom = models.CharField("nom", max_length=100, unique=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "région"
        verbose_name_plural = "régions"

    def __str__(self) -> str:
        return f"{self.code} — {self.nom}"


class Circuit(Fermable):
    region = models.ForeignKey(
        Region, on_delete=models.PROTECT, related_name="circuits", verbose_name="région"
    )
    nom = models.CharField("nom", max_length=150)

    class Meta:
        ordering = ["region__code", "nom"]
        verbose_name = "circuit"
        verbose_name_plural = "circuits"
        constraints = [
            models.UniqueConstraint(fields=["region", "nom"], name="circuit_unique_par_region")
        ]

    def __str__(self) -> str:
        return f"Circuit de {self.nom}"


class Paroisse(Fermable):
    circuit = models.ForeignKey(
        Circuit, on_delete=models.PROTECT, related_name="paroisses", verbose_name="circuit"
    )
    nom = models.CharField("nom", max_length=255)

    class Meta:
        ordering = ["circuit__region__code", "circuit__nom", "nom"]
        verbose_name = "paroisse"
        verbose_name_plural = "paroisses"
        constraints = [
            models.UniqueConstraint(fields=["circuit", "nom"], name="paroisse_unique_par_circuit")
        ]

    def __str__(self) -> str:
        return self.nom

    @property
    def region(self) -> Region:
        return self.circuit.region
