"""Trésorerie : mobile money, cotisations spéciales, reversements mensuels (13/11/2026).

Seul `apps/tresorerie/services.py` écrit dans ces tables. Rien ne s'efface.
- Un seul numéro mobile money, au nom du Bureau national ; le paiement part toujours du site.
- Les parts des cotisations mensuelles payées par mobile money sont reversées chaque mois par le
  BN au numéro du Trésorier de chaque paroisse, circuit et région.
"""

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


def _compte(nom):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=nom,
    )


class SansSuppression(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Une donnée financière ne se supprime pas.")


class NumeroMobileMoney(SansSuppression):
    """Numéro mobile money d'un bureau (celui de son Trésorier) ; enregistré par le BN seulement."""

    cle = models.CharField("unité (clé)", max_length=30, unique=True)
    libelle = models.CharField("unité", max_length=200)
    numero = models.CharField("numéro mobile money", max_length=20)
    titulaire = models.CharField("titulaire du numéro", max_length=200, blank=True)
    modifie_par = _compte("enregistré par")
    date = models.DateTimeField("le", auto_now=True)

    class Meta:
        verbose_name = "numéro mobile money d'un bureau"
        verbose_name_plural = "numéros mobile money des bureaux"
        ordering = ["cle"]


class TypeMontant(models.TextChoices):
    FIXE = "fixe", "Montant fixe"
    MINIMUM = "minimum", "Montant minimum (on peut payer plus)"
    LIBRE = "libre", "Montant libre (comme un don)"


class PourMembres(models.TextChoices):
    TOUS = "tous", "Tous les membres"
    CERTAINS = "certains", "Certains membres (critères)"
    AUCUN = "aucun", "Aucun membre (bureaux seulement)"


class CotisationSpeciale(SansSuppression):
    libelle = models.CharField("libellé", max_length=200)
    description = models.TextField("description", blank=True)
    echeance = models.DateField("échéance", null=True, blank=True)
    type_montant = models.CharField(
        "type de montant", max_length=10, choices=TypeMontant.choices, default=TypeMontant.FIXE
    )
    montant = models.PositiveIntegerField("montant (F CFA)", null=True, blank=True)
    pour_membres = models.CharField(
        "membres concernés", max_length=10, choices=PourMembres.choices, default=PourMembres.TOUS
    )
    criteres = models.JSONField("critères (mêmes filtres que les listes)", default=dict, blank=True)
    pour_bureaux = models.JSONField(
        "bureaux concernés (paroisse, circuit, region)", default=list, blank=True
    )
    ouverte = models.BooleanField("ouverte", default=True)
    cree_par = _compte("créée par")
    date_creation = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "cotisation spéciale"
        verbose_name_plural = "cotisations spéciales"
        ordering = ["-date_creation"]

    def __str__(self) -> str:
        return self.libelle


class NaturePaiement(models.TextChoices):
    MENSUELLE = "mensuelle", "Cotisation mensuelle"
    SPECIALE = "speciale", "Cotisation spéciale"


class EtatPaiement(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente de confirmation"
    CONFIRME = "confirme", "Confirmé"
    ECHOUE = "echoue", "Non abouti"
    ANOMALIE = "anomalie", "Reçu mais non affecté (à régulariser par le BN)"


class Paiement(SansSuppression):
    """Un paiement mobile money parti du site vers le numéro du BN."""

    reference = models.CharField("référence", max_length=40, unique=True)
    payeur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="paiements"
    )
    nature = models.CharField("nature", max_length=10, choices=NaturePaiement.choices)
    cotisation_speciale = models.ForeignKey(
        CotisationSpeciale, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    montant = models.PositiveIntegerField("montant (F CFA)")
    objet = models.JSONField("ce qui est payé", default=dict)
    description = models.CharField("description", max_length=300, blank=True)
    plateforme = models.CharField("plateforme", max_length=30, default="simulee")
    etat = models.CharField(
        "état", max_length=12, choices=EtatPaiement.choices, default=EtatPaiement.EN_ATTENTE
    )
    message = models.CharField("message", max_length=300, blank=True)
    date_creation = models.DateTimeField("créé le", auto_now_add=True)
    date_confirmation = models.DateTimeField("confirmé le", null=True, blank=True)

    class Meta:
        verbose_name = "paiement mobile money"
        ordering = ["-date_creation"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.montant} F ({self.get_etat_display()})"


class Contribution(SansSuppression):
    """Paiement (total ou partiel) d'une cotisation spéciale, par un membre ou un bureau."""

    cotisation = models.ForeignKey(
        CotisationSpeciale, on_delete=models.PROTECT, related_name="contributions"
    )
    membre = models.ForeignKey(
        "membres.Membre",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contributions",
    )
    unite_cle = models.CharField("au nom du bureau (clé)", max_length=30, blank=True)
    unite_libelle = models.CharField("au nom du bureau", max_length=200, blank=True)
    montant = models.PositiveIntegerField("montant (F CFA)")
    quittance = models.CharField("numéro de quittance", max_length=20, unique=True)
    paiement = models.ForeignKey(Paiement, on_delete=models.PROTECT, related_name="contributions")
    date = models.DateTimeField("le", auto_now_add=True)

    class Meta:
        verbose_name = "contribution à une cotisation spéciale"
        ordering = ["-date"]


class EtatReversement(models.TextChoices):
    PREPARE = "prepare", "Préparé (à valider)"
    VALIDE = "valide", "Validé (à envoyer)"
    ENVOYE = "envoye", "Envoyé"


class Reversement(SansSuppression):
    """Part mensuelle due par le BN à une paroisse, un circuit ou une région."""

    mois = models.DateField("mois")
    cle = models.CharField("unité (clé)", max_length=30)
    libelle = models.CharField("unité", max_length=200)
    niveau = models.CharField("niveau", max_length=10)
    montant = models.PositiveIntegerField("montant (F CFA)")
    numero = models.CharField("numéro du Trésorier", max_length=20, blank=True)
    etat = models.CharField(
        "état", max_length=10, choices=EtatReversement.choices, default=EtatReversement.PREPARE
    )
    prepare_par = _compte("préparé par")
    date_preparation = models.DateTimeField("préparé le", auto_now_add=True)
    valide_par = _compte("validé par")
    date_validation = models.DateTimeField("validé le", null=True, blank=True)
    envoye_par = _compte("envoyé par")
    date_envoi = models.DateTimeField("envoyé le", null=True, blank=True)
    reference_envoi = models.CharField("référence de l'envoi", max_length=60, blank=True)

    class Meta:
        verbose_name = "reversement mensuel"
        verbose_name_plural = "reversements mensuels"
        ordering = ["mois", "niveau", "libelle"]
        constraints = [models.UniqueConstraint(fields=["mois", "cle"], name="reversement_unique")]
