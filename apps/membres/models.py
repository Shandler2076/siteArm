"""Membres : fiche, compteur de matricules, parcours (affectations), photos d'identité."""

import datetime
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.membres.stockage import stockage_prive
from apps.organisation.models import Circuit, Paroisse, Region


class Sexe(models.TextChoices):
    MASCULIN = "M", "Masculin"
    FEMININ = "F", "Féminin"


class SituationMatrimoniale(models.TextChoices):
    CELIBATAIRE = "celibataire", "Célibataire"
    MARIE = "marie", "Marié(e)"
    VEUF = "veuf", "Veuf / veuve"
    DIVORCE = "divorce", "Divorcé(e)"


class Categorie(models.TextChoices):
    ACTIF = "actif", "Membre actif"
    HONNEUR = "honneur", "Membre d'honneur"
    SYMPATHISANT = "sympathisant", "Membre sympathisant"


class Statut(models.TextChoices):
    ACTIF = "actif", "Actif"
    SANCTIONNE = "sanctionne", "Sanctionné"
    EXCLU = "exclu", "Exclu"
    DEMISSIONNAIRE = "demissionnaire", "Démissionnaire"
    DECEDE = "decede", "Décédé"


def cle_nom(texte: str) -> str:
    """Forme de comparaison : sans accents, majuscules, tirets et espaces multiples réduits."""
    sans_accents = "".join(
        c for c in unicodedata.normalize("NFKD", texte or "") if not unicodedata.combining(c)
    )
    return re.sub(r"[\s\-]+", " ", sans_accents.upper()).strip()


valider_telephone = RegexValidator(
    r"^\+?[0-9 ]{8,20}$", "Numéro de téléphone invalide (chiffres, espaces et + uniquement)."
)
valider_npi = RegexValidator(r"^\d{10}$", "Le NPI comporte 10 chiffres.")


class Membre(models.Model):
    # Identité
    nom = models.CharField("nom", max_length=100)
    prenoms = models.CharField("prénoms", max_length=150)
    sexe = models.CharField("sexe", max_length=1, choices=Sexe.choices)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    lieu_naissance = models.CharField("lieu de naissance", max_length=150, blank=True)
    situation_matrimoniale = models.CharField(
        "situation matrimoniale", max_length=20, choices=SituationMatrimoniale.choices, blank=True
    )
    npi = models.CharField("NPI", max_length=10, blank=True, validators=[valider_npi])
    photo_cip = models.FileField(
        "photo du CIP", storage=stockage_prive, upload_to="cip/", blank=True
    )
    # Contact
    telephone = models.CharField("téléphone", max_length=20, validators=[valider_telephone])
    whatsapp = models.CharField(
        "WhatsApp", max_length=20, blank=True, validators=[valider_telephone]
    )
    email = models.EmailField("email", blank=True)
    quartier = models.CharField("quartier", max_length=150, blank=True)
    ville = models.CharField("ville", max_length=100, blank=True)
    # Autres
    profession = models.CharField("profession", max_length=150, blank=True)
    urgence_nom = models.CharField("personne à contacter (nom)", max_length=150, blank=True)
    urgence_telephone = models.CharField(
        "personne à contacter (téléphone)",
        max_length=20,
        blank=True,
        validators=[valider_telephone],
    )
    # Armée du Salut
    annee_integration = models.PositiveSmallIntegerField("année d'intégration")
    paroisse_integration = models.ForeignKey(
        Paroisse, on_delete=models.PROTECT, related_name="+", verbose_name="paroisse d'intégration"
    )
    region_integration = models.ForeignKey(
        Region, on_delete=models.PROTECT, related_name="+", verbose_name="région d'intégration"
    )
    matricule = models.CharField("matricule", max_length=14, unique=True)
    categorie = models.CharField(
        "catégorie", max_length=20, choices=Categorie.choices, default=Categorie.ACTIF
    )
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    compte = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="membre",
        verbose_name="compte",
    )
    cle_identite = models.CharField(
        "clé de recherche des doublons", max_length=260, editable=False, db_index=True
    )
    date_enregistrement = models.DateTimeField("date d'enregistrement", auto_now_add=True)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="enregistré par",
    )

    class Meta:
        verbose_name = "membre"
        verbose_name_plural = "membres"
        ordering = ["matricule"]
        constraints = [
            models.UniqueConstraint(
                fields=["npi"],
                condition=~Q(npi=""),
                name="npi_unique",
                violation_error_message="Ce NPI est déjà utilisé par un autre membre.",
            )
        ]
        permissions = [
            ("gerer_membres", "Gérer les membres (Bureau national)"),
            ("voir_cip", "Voir la photo du CIP"),
        ]

    def __str__(self) -> str:
        return f"{self.matricule} — {self.nom_complet}"

    def clean(self):
        annee_max = timezone.localdate().year
        if self.annee_integration is not None and not (1900 <= self.annee_integration <= annee_max):
            raise ValidationError(
                {"annee_integration": f"L'année d'intégration doit être entre 1900 et {annee_max}."}
            )

    def save(self, *args, **kwargs):
        self.cle_identite = f"{cle_nom(self.nom)} | {cle_nom(self.prenoms)}"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("On ne supprime pas un membre.")

    @property
    def nom_complet(self) -> str:
        return f"{self.nom.upper()} {self.prenoms}".strip()

    def age(self, aujourdhui: datetime.date | None = None) -> int | None:
        if not self.date_naissance:
            return None
        j = aujourdhui or timezone.localdate()
        n = self.date_naissance
        return j.year - n.year - ((j.month, j.day) < (n.month, n.day))

    @property
    def affectation_actuelle(self) -> "Affectation | None":
        return self.affectations.filter(date_fin__isnull=True).first()

    @property
    def photo_acceptee(self) -> "PhotoIdentite | None":
        return self.photos.filter(etat=EtatPhoto.ACCEPTEE).order_by("-date_decision").first()


class CompteurMatricule(models.Model):
    annee = models.PositiveSmallIntegerField("année")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, verbose_name="région")
    dernier_numero = models.PositiveSmallIntegerField("dernier numéro attribué", default=0)

    class Meta:
        verbose_name = "compteur de matricules"
        verbose_name_plural = "compteurs de matricules"
        constraints = [models.UniqueConstraint(fields=["annee", "region"], name="compteur_unique")]

    def __str__(self) -> str:
        return f"{self.annee} — région {self.region.code} : {self.dernier_numero}"


class Affectation(models.Model):
    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="affectations")
    paroisse = models.ForeignKey(Paroisse, on_delete=models.PROTECT, related_name="+")
    circuit_a_date = models.ForeignKey(
        Circuit, on_delete=models.PROTECT, related_name="+", verbose_name="circuit à cette date"
    )
    region_a_date = models.ForeignKey(
        Region, on_delete=models.PROTECT, related_name="+", verbose_name="région à cette date"
    )
    date_debut = models.DateField("date de début")
    date_fin = models.DateField("date de fin", null=True, blank=True)
    motif = models.CharField("motif", max_length=200)

    class Meta:
        verbose_name = "affectation"
        verbose_name_plural = "affectations (parcours)"
        ordering = ["date_debut", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["membre"], condition=Q(date_fin=None), name="une_affectation_ouverte"
            )
        ]

    def __str__(self) -> str:
        return f"{self.membre.matricule} — {self.paroisse} ({self.date_debut})"


class EtatPhoto(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    ACCEPTEE = "acceptee", "Acceptée"
    REFUSEE = "refusee", "Refusée"
    REMPLACEE = "remplacee", "Remplacée"


class PhotoIdentite(models.Model):
    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="photos")
    fichier = models.ImageField("photo", storage=stockage_prive, upload_to="photos/")
    etat = models.CharField(
        "état", max_length=20, choices=EtatPhoto.choices, default=EtatPhoto.EN_ATTENTE
    )
    motif_refus = models.CharField("motif du refus", max_length=300, blank=True)
    date_depot = models.DateTimeField("date de dépôt", auto_now_add=True)
    date_decision = models.DateTimeField("date de la décision", null=True, blank=True)
    decide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="décidé par",
    )

    class Meta:
        verbose_name = "photo d'identité"
        verbose_name_plural = "photos d'identité"
        ordering = ["-date_depot"]

    def __str__(self) -> str:
        return f"Photo de {self.membre.matricule} ({self.get_etat_display()})"
