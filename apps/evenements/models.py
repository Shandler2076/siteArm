"""Événements nationaux, sections, convocations et présences (cahier des charges § 17).

Le modèle `Session` porte les **sections** d'un événement (décision du 13/11/2026 : le mot
affiché est « section »).

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
    avec_sections = models.BooleanField("organiser en sections", default=False)
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
    """Section d'un événement (ex. « Section Mer », « Section Culte »), créée à la main."""

    evenement = models.ForeignKey(Evenement, on_delete=models.PROTECT, related_name="sessions")
    nom = models.CharField("nom", max_length=120)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "section"
        ordering = ["ordre", "pk"]
        constraints = [models.UniqueConstraint(fields=["evenement", "nom"], name="session_unique")]

    def __str__(self) -> str:
        return self.nom


class Presence(models.TextChoices):
    NON_POINTE = "", "Non pointé"
    PRESENT = "present", "Présent"
    ABSENT = "absent", "Absent"
    EXCUSE = "excuse", "Excusé"


class Role(models.TextChoices):
    """« Invité(e) en tant que » (décisions du 13/11/2026)."""

    TRAVAILLEUR = "travailleur", "Travailleur"
    SUPERVISEUR = "superviseur", "Superviseur"
    BUREAU_ORGANISATION = "bureau_organisation", "Bureau d'organisation"
    OFFICIEL = "officiel", "Officiel"
    AUTRE = "autre", "Autre (à préciser)"


class Formule(models.TextChoices):
    TRAVAILLER = "travailler", "est autorisé(e) à travailler"
    PARTICIPER = "participer", "est autorisé(e) à participer"


def formule_par_defaut(role: str) -> str:
    return Formule.TRAVAILLER if role == Role.TRAVAILLEUR else Formule.PARTICIPER


def nouveau_jeton() -> str:
    return secrets.token_urlsafe(24)  # 32 caractères, impossible à deviner


class Convocation(models.Model):
    evenement = models.ForeignKey(Evenement, on_delete=models.PROTECT, related_name="convocations")
    membre = models.ForeignKey(
        "membres.Membre", on_delete=models.PROTECT, related_name="convocations"
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="convocations",
        verbose_name="section",
    )
    role = models.CharField(
        "invité(e) en tant que", max_length=20, choices=Role.choices, default=Role.TRAVAILLEUR
    )
    role_autre = models.CharField("autre rôle (écrit à la main)", max_length=100, blank=True)
    formule = models.CharField(
        "formule de l'autorisation", max_length=12, choices=Formule.choices, blank=True
    )
    bureau_libelle = models.CharField("bureau représenté", max_length=200, blank=True)
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

    @property
    def formule_effective(self) -> str:
        return self.formule or formule_par_defaut(self.role)

    @property
    def texte_formule(self) -> str:
        """« Est autorisé(e) à travailler » ou « Est autorisé(e) à participer »."""
        return (
            Formule(self.formule_effective).label[0].upper()
            + Formule(self.formule_effective).label[1:]
        )

    @property
    def libelle_role(self) -> str:
        """« Superviseur », « Bureau d'organisation », ou le rôle écrit à la main."""
        if self.role == Role.AUTRE:
            return self.role_autre or "Autre"
        if self.role == "bureau":  # ancien rôle (avant le 13/11/2026)
            return "Bureau d'organisation"
        return self.get_role_display()

    @property
    def texte_role(self) -> str:
        """« Invité(e) en tant que superviseur — Section Mer », « … officiel »."""
        texte = f"Invité(e) en tant que {self.libelle_role[0].lower()}{self.libelle_role[1:]}"
        return f"{texte} — {self.session.nom}" if self.session_id else texte
