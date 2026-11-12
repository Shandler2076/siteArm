"""Cotisations mensuelles (CM) : réglages, versements, mois cotisés, parts reçues.

Seul `apps/cotisations/services.py` écrit dans ces tables (cahier des charges § 16).
"""

import datetime

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Q


def premier_du_mois(jour: datetime.date) -> datetime.date:
    return jour.replace(day=1)


class ParametresCotisations(models.Model):
    """Une seule ligne : le mois de mise en service (rien n'est dû avant)."""

    mois_depart = models.DateField("premier mois suivi", null=True, blank=True)

    class Meta:
        verbose_name = "paramètres des cotisations"
        verbose_name_plural = "paramètres des cotisations"

    @classmethod
    def courant(cls) -> "ParametresCotisations":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Tarif(models.Model):
    """Montant mensuel et répartition en pourcentages, à compter d'un mois."""

    date_effet = models.DateField("à compter du mois", unique=True)
    montant = models.PositiveIntegerField("montant mensuel (F CFA)")
    part_paroisse = models.PositiveSmallIntegerField("part de la paroisse (%)")
    part_circuit = models.PositiveSmallIntegerField("part du circuit (%)")
    part_region = models.PositiveSmallIntegerField("part de la région (%)")
    part_national = models.PositiveSmallIntegerField("part du national (%)")

    class Meta:
        verbose_name = "tarif"
        ordering = ["date_effet"]

    def __str__(self) -> str:
        return f"{self.montant} F à compter de {self.date_effet:%m/%Y}"

    def clean(self):
        total = self.part_paroisse + self.part_circuit + self.part_region + self.part_national
        if total != 100:
            raise ValidationError(f"Les parts doivent faire 100 % au total (ici {total} %).")
        if self.montant <= 0:
            raise ValidationError("Le montant mensuel doit être positif.")

    @property
    def parts(self) -> dict[str, int]:
        return {
            "paroisse": self.part_paroisse,
            "circuit": self.part_circuit,
            "region": self.part_region,
            "national": self.part_national,
        }


TARIF_PAR_DEFAUT = dict(
    montant=100, part_paroisse=30, part_circuit=20, part_region=20, part_national=30
)


def tarifs() -> list[Tarif]:
    return list(Tarif.objects.order_by("date_effet"))


def tarif_parmi(liste: list[Tarif], mois: datetime.date) -> Tarif:
    choisi = None
    for t in liste:
        if t.date_effet <= mois:
            choisi = t
    return choisi or Tarif(date_effet=datetime.date(2000, 1, 1), **TARIF_PAR_DEFAUT)


def tarif_du(mois: datetime.date) -> Tarif:
    return tarif_parmi(tarifs(), premier_du_mois(mois))


class EtatVersement(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente de validation"
    VALIDE = "valide", "Validé"
    REFUSE = "refuse", "Refusé"
    ANNULE = "annule", "Annulé"


def _compte(nom):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=nom,
    )


class Versement(models.Model):
    membre = models.ForeignKey(
        "membres.Membre", on_delete=models.PROTECT, related_name="versements"
    )
    paroisse = models.ForeignKey(
        "organisation.Paroisse",
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="paroisse qui a encaissé",
    )
    montant = models.PositiveIntegerField("montant (F CFA)")
    date_versement = models.DateField("date du versement")
    etat = models.CharField(
        "état", max_length=12, choices=EtatVersement.choices, default=EtatVersement.EN_ATTENTE
    )
    saisi_par = _compte("saisi par")
    date_saisie = models.DateTimeField("saisi le", auto_now_add=True)
    valide_par = _compte("validé ou refusé par")
    date_validation = models.DateTimeField("validé ou refusé le", null=True, blank=True)
    motif = models.CharField("motif (refus ou annulation)", max_length=300, blank=True)
    numero_recu = models.CharField("numéro de reçu", max_length=20, blank=True)
    parts = models.JSONField("parts (F CFA)", default=dict, blank=True)

    class Meta:
        verbose_name = "versement"
        ordering = ["-date_versement", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["numero_recu"], condition=~Q(numero_recu=""), name="recu_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.montant} F — {self.membre} ({self.get_etat_display()})"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Un versement ne se supprime pas : il s'annule.")


class MoisCotise(models.Model):
    versement = models.ForeignKey(Versement, on_delete=models.PROTECT, related_name="mois")
    membre = models.ForeignKey(
        "membres.Membre", on_delete=models.PROTECT, related_name="mois_cotises"
    )
    mois = models.DateField("mois")
    montant = models.PositiveIntegerField("montant (F CFA)")
    actif = models.BooleanField("compte (en attente ou validé)", default=True)

    class Meta:
        verbose_name = "mois cotisé"
        verbose_name_plural = "mois cotisés"
        ordering = ["mois"]
        constraints = [
            models.UniqueConstraint(
                fields=["membre", "mois"], condition=Q(actif=True), name="un_versement_par_mois"
            )
        ]

    def delete(self, *args, **kwargs):
        raise PermissionDenied("On ne supprime pas un mois cotisé.")


class NiveauPart(models.TextChoices):
    CIRCUIT = "circuit", "Circuit"
    REGION = "region", "Région"
    NATIONAL = "national", "Bureau national"


class PartRecue(models.Model):
    """Le niveau a reçu sa part des versements d'une paroisse validés dans un mois donné."""

    niveau = models.CharField("niveau", max_length=10, choices=NiveauPart.choices)
    paroisse = models.ForeignKey(
        "organisation.Paroisse", on_delete=models.PROTECT, related_name="+"
    )
    mois_validation = models.DateField("mois de validation")
    montant = models.PositiveIntegerField("montant (F CFA)")
    marquee_par = _compte("marquée par")
    date = models.DateTimeField("le", auto_now_add=True)

    class Meta:
        verbose_name = "part reçue"
        verbose_name_plural = "parts reçues"
        constraints = [
            models.UniqueConstraint(
                fields=["niveau", "paroisse", "mois_validation"], name="part_recue_unique"
            )
        ]

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Une part reçue ne se supprime pas.")
