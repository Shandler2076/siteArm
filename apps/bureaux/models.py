"""Fonctions des bureaux (règlement intérieur) et mandats des membres."""

import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.membres.models import Membre
from apps.organisation.models import Circuit, Paroisse, Region


class Niveau(models.TextChoices):
    PAROISSE = "paroisse", "Unité paroissiale"
    CIRCUIT = "circuit", "Section de Circuit"
    REGION = "region", "Bureau Régional de Coordination"
    NATIONAL = "national", "Bureau National de Commandement"


UNITES = ("paroisse", "circuit", "region")


class Fonction(models.Model):
    nom = models.CharField("nom", max_length=150)
    niveau = models.CharField("niveau", max_length=10, choices=Niveau.choices)
    droit_gerer = models.BooleanField("droit de gérer le site", default=False)
    duree_mandat_annees = models.PositiveSmallIntegerField("durée du mandat (années)", default=2)
    membre_du_bureau = models.BooleanField("membre du bureau", default=True)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "fonction"
        verbose_name_plural = "fonctions"
        ordering = ["niveau", "ordre"]
        constraints = [
            models.UniqueConstraint(fields=["niveau", "nom"], name="fonction_unique_par_niveau")
        ]

    def __str__(self) -> str:
        return self.nom


def _ajouter_annees(jour: datetime.date, annees: int) -> datetime.date:
    try:
        return jour.replace(year=jour.year + annees)
    except ValueError:  # 29 février
        return jour.replace(year=jour.year + annees, day=28)


class MandatQuerySet(models.QuerySet):
    def en_cours(self, jour: datetime.date | None = None):
        j = jour or timezone.localdate()
        return self.filter(date_debut__lte=j).filter(Q(date_fin__isnull=True) | Q(date_fin__gt=j))


class Mandat(models.Model):
    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="mandats")
    fonction = models.ForeignKey(Fonction, on_delete=models.PROTECT, related_name="mandats")
    paroisse = models.ForeignKey(
        Paroisse, null=True, blank=True, on_delete=models.PROTECT, related_name="mandats"
    )
    circuit = models.ForeignKey(
        Circuit, null=True, blank=True, on_delete=models.PROTECT, related_name="mandats"
    )
    region = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="mandats",
        verbose_name="région",
    )
    date_debut = models.DateField("date de début")
    date_fin_prevue = models.DateField("date de fin prévue", blank=True)
    date_fin = models.DateField("date de fin", null=True, blank=True)
    alerte_echeance_le = models.DateField("alerte d'échéance envoyée le", null=True, blank=True)
    alerte_echu_le = models.DateField("alerte de mandat échu envoyée le", null=True, blank=True)
    installe_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="installé par",
    )

    objects = MandatQuerySet.as_manager()

    class Meta:
        verbose_name = "mandat"
        verbose_name_plural = "mandats"
        ordering = ["-date_debut"]

    def __str__(self) -> str:
        unite = self.unite
        return f"{self.fonction} — {unite or 'national'} — {self.membre.nom_complet}"

    @property
    def unite(self):
        return getattr(self, self.fonction.niveau, None) if self.fonction.niveau in UNITES else None

    def clean(self):
        if not self.fonction_id:
            return
        niveau = self.fonction.niveau
        renseignees = {u for u in UNITES if getattr(self, f"{u}_id")}
        attendu = {niveau} if niveau in UNITES else set()
        if renseignees != attendu:
            raise ValidationError("L'unité ne correspond pas au niveau de la fonction.")
        if self.date_fin and self.date_debut and self.date_fin <= self.date_debut:
            raise ValidationError({"date_fin": "La date de fin doit suivre la date de début."})

    def save(self, *args, **kwargs):
        if not self.date_fin_prevue:
            self.date_fin_prevue = _ajouter_annees(
                self.date_debut, self.fonction.duree_mandat_annees
            )
        super().save(*args, **kwargs)

    def est_en_cours(self, jour: datetime.date | None = None) -> bool:
        j = jour or timezone.localdate()
        return self.date_debut <= j and (self.date_fin is None or self.date_fin > j)
