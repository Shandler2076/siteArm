"""Lots d'enregistrement (fichier Excel d'une région) et leurs lignes."""

from collections import Counter

from django.conf import settings
from django.db import models

from apps.membres.models import Membre
from apps.membres.stockage import stockage_prive
from apps.organisation.models import Region


class EtatLot(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    VALIDE = "valide", "Validé"


class EtatLigne(models.TextChoices):
    CORRECTE = "correcte", "Correcte"
    DOUBLON = "doublon", "Doublon possible"
    ERREUR = "erreur", "Erreur"
    ECARTEE = "ecartee", "Écartée"
    GARDEE = "gardee", "Doublon gardé"


A_CREER = (EtatLigne.CORRECTE, EtatLigne.GARDEE)


class Lot(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, verbose_name="région")
    fichier = models.FileField("fichier", storage=stockage_prive, upload_to="lots/", blank=True)
    nom_fichier = models.CharField("nom du fichier", max_length=200, blank=True)
    fichiers = models.JSONField("fichiers déposés", default=list, blank=True)
    etat = models.CharField(
        "état", max_length=10, choices=EtatLot.choices, default=EtatLot.BROUILLON
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    date_creation = models.DateTimeField("date de dépôt", auto_now_add=True)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    date_validation = models.DateTimeField("date de validation", null=True, blank=True)

    class Meta:
        verbose_name = "lot"
        verbose_name_plural = "lots"
        ordering = ["-date_creation"]

    def __str__(self) -> str:
        return f"Lot n° {self.pk} — {self.region.nom}"

    @property
    def nb_par_etat(self) -> dict[str, int]:
        return dict(Counter(self.lignes.values_list("etat", flat=True)))

    @property
    def validable(self) -> bool:
        etats = self.nb_par_etat
        bloquants = etats.get(EtatLigne.ERREUR, 0) + etats.get(EtatLigne.DOUBLON, 0)
        a_creer = sum(etats.get(e, 0) for e in A_CREER)
        return self.etat == EtatLot.BROUILLON and bloquants == 0 and a_creer > 0


class LigneLot(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="lignes")
    numero = models.PositiveIntegerField("ligne Excel")
    brutes = models.JSONField("valeurs lues", default=dict)
    donnees = models.JSONField("valeurs normalisées", default=dict)
    etat = models.CharField(
        "état", max_length=10, choices=EtatLigne.choices, default=EtatLigne.CORRECTE
    )
    erreurs = models.JSONField("erreurs", default=list)
    doublons = models.JSONField("doublons possibles", default=list)
    corrigee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    date_correction = models.DateTimeField(null=True, blank=True)
    membre = models.ForeignKey(
        Membre, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        verbose_name = "ligne de lot"
        verbose_name_plural = "lignes de lot"
        ordering = ["numero"]
        constraints = [
            models.UniqueConstraint(fields=["lot", "numero"], name="ligne_unique_par_lot")
        ]

    def __str__(self) -> str:
        return f"{self.lot} — ligne {self.numero}"
