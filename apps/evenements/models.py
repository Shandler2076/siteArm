"""Événements nationaux, sessions, convocations et présences (cahier des charges § 17).

Seul `apps/evenements/services.py` écrit dans ces tables. Rien ne s'efface.
"""

import datetime
import secrets

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q


def _compte(nom):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=nom,
    )


class EtatEvenement(models.TextChoices):
    PREVU = "prevu", "Prévu"
    ANNULE = "annule", "Annulé"


class Evenement(models.Model):
    nom = models.CharField("dénomination", max_length=200)
    debut = models.DateTimeField("début")
    fin = models.DateTimeField("fin", null=True, blank=True)
    lieu = models.CharField("lieu", max_length=200, blank=True)
    description = models.TextField("description", blank=True)
    avec_autorisation = models.BooleanField("générer une autorisation", default=False)
    validite_debut = models.DateTimeField("autorisation valable à partir du", null=True, blank=True)
    validite_heures = models.PositiveSmallIntegerField(
        "durée de validité de l'autorisation (heures)", default=24
    )
    etat = models.CharField(
        "état", max_length=10, choices=EtatEvenement.choices, default=EtatEvenement.PREVU
    )
    motif_annulation = models.CharField("motif de l'annulation", max_length=300, blank=True)
    cree_par = _compte("créé par")
    date_creation = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "événement"
        ordering = ["-debut"]

    def __str__(self) -> str:
        return f"{self.nom} ({self.debut:%d/%m/%Y})"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Un événement ne se supprime pas : il s'annule.")

    @property
    def annule(self) -> bool:
        return self.etat == EtatEvenement.ANNULE

    @property
    def debut_validite(self) -> datetime.datetime:
        return self.validite_debut or self.debut

    @property
    def fin_validite(self) -> datetime.datetime:
        return self.debut_validite + datetime.timedelta(hours=self.validite_heures)


class Session(models.Model):
    evenement = models.ForeignKey(Evenement, on_delete=models.PROTECT, related_name="sessions")
    nom = models.CharField("nom", max_length=120)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        ordering = ["ordre", "pk"]
        constraints = [models.UniqueConstraint(fields=["evenement", "nom"], name="session_unique")]

    def __str__(self) -> str:
        return self.nom


class Presence(models.TextChoices):
    NON_POINTE = "", "Non pointé"
    PRESENT = "present", "Présent"
    ABSENT = "absent", "Absent"
    EXCUSE = "excuse", "Excusé"


def nouveau_jeton() -> str:
    return secrets.token_urlsafe(24)  # 32 caractères, impossible à deviner


class Convocation(models.Model):
    evenement = models.ForeignKey(Evenement, on_delete=models.PROTECT, related_name="convocations")
    membre = models.ForeignKey(
        "membres.Membre", on_delete=models.PROTECT, related_name="convocations"
    )
    session = models.ForeignKey(
        Session, on_delete=models.PROTECT, null=True, blank=True, related_name="convocations"
    )
    active = models.BooleanField("active", default=True)
    jeton = models.CharField("jeton de vérification", max_length=64, unique=True)
    presence = models.CharField(
        "présence", max_length=10, choices=Presence.choices, default="", blank=True
    )
    pointe_par = _compte("pointé par")
    date_pointage = models.DateTimeField("pointé le", null=True, blank=True)
    convoque_par = _compte("convoqué par")
    date_convocation = models.DateTimeField("convoqué le", auto_now_add=True)
    motif_retrait = models.CharField("motif du retrait", max_length=300, blank=True)

    class Meta:
        ordering = ["membre__nom", "membre__prenoms"]
        constraints = [
            models.UniqueConstraint(
                fields=["evenement", "membre"],
                condition=Q(active=True),
                name="une_convocation_active",
            )
        ]

    def __str__(self) -> str:
        return f"{self.membre} — {self.evenement}"

    def save(self, *args, **kwargs):
        if not self.jeton:
            self.jeton = nouveau_jeton()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Une convocation ne se supprime pas : elle se retire.")
