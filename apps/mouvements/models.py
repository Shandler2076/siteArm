"""Mouvements de la vie d'un membre : mutations, signalements et historique."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.membres.models import Categorie, Membre, Statut
from apps.organisation.models import Paroisse


class TypeHistorique(models.TextChoices):
    STATUT = "statut", "Statut"
    CATEGORIE = "categorie", "Catégorie"


class TypeSignalement(models.TextChoices):
    DECES = "deces", "Décès"
    DEMISSION = "demission", "Démission"
    REHABILITATION = "rehabilitation", "Réhabilitation"
    CATEGORIE = "categorie", "Changement de catégorie"


class EtatDemande(models.TextChoices):
    AVIS = "avis", "En attente d'avis"
    BN = "bn", "En attente du BN"
    VALIDEE = "validee", "Validée"
    REFUSEE = "refusee", "Refusée"
    ANNULEE = "annulee", "Annulée"


EN_COURS = (EtatDemande.AVIS, EtatDemande.BN)


def _compte(related_name="+", verbose_name="par", null=True):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=null,
        blank=null,
        on_delete=models.SET_NULL if null else models.PROTECT,
        related_name=related_name,
        verbose_name=verbose_name,
    )


class HistoriqueMembre(models.Model):
    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="historique")
    date = models.DateTimeField("enregistré le", auto_now_add=True)
    type = models.CharField("type", max_length=20, choices=TypeHistorique.choices)
    ancien = models.CharField("ancienne valeur", max_length=20)
    nouveau = models.CharField("nouvelle valeur", max_length=20)
    date_effet = models.DateField("date d'effet")
    motif = models.CharField("motif", max_length=200)
    reference = models.CharField("référence", max_length=120, blank=True)
    par = _compte()

    class Meta:
        verbose_name = "événement de l'historique"
        verbose_name_plural = "historique des membres"
        ordering = ["-date_effet", "-pk"]

    def __str__(self) -> str:
        return f"{self.membre.matricule} — {self.libelle}"

    @property
    def libelle(self) -> str:
        choix = Statut if self.type == TypeHistorique.STATUT else Categorie
        libelles = dict(choix.choices)
        ancien = libelles.get(self.ancien, self.ancien)
        nouveau = libelles.get(self.nouveau, self.nouveau)
        return f"{self.get_type_display()} : {ancien} → {nouveau}"


class Mutation(models.Model):
    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="mutations")
    paroisse_depart = models.ForeignKey(
        Paroisse, on_delete=models.PROTECT, related_name="+", verbose_name="paroisse de départ"
    )
    paroisse_arrivee = models.ForeignKey(
        Paroisse, on_delete=models.PROTECT, related_name="+", verbose_name="paroisse d'arrivée"
    )
    etat = models.CharField(
        "état", max_length=10, choices=EtatDemande.choices, default=EtatDemande.AVIS
    )
    motif = models.CharField("motif", max_length=300, blank=True)
    demandee_par = _compte(verbose_name="demandée par", null=False)
    date_demande = models.DateTimeField("date de la demande", auto_now_add=True)
    decidee_par = _compte(verbose_name="décidée par")
    date_decision = models.DateTimeField("date de la décision", null=True, blank=True)
    commentaire_decision = models.CharField(
        "commentaire de la décision", max_length=300, blank=True
    )

    class Meta:
        verbose_name = "mutation"
        verbose_name_plural = "mutations"
        ordering = ["-date_demande", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["membre"],
                condition=Q(etat__in=["avis", "bn"]),
                name="une_mutation_en_cours",
            )
        ]

    def __str__(self) -> str:
        return f"Mutation n° {self.pk} — {self.membre.matricule}"

    @property
    def en_cours(self) -> bool:
        return self.etat in EN_COURS


class AvisMutation(models.Model):
    NIVEAUX = [("circuit", "Circuit de départ"), ("region", "Région de départ")]

    mutation = models.ForeignKey(Mutation, on_delete=models.CASCADE, related_name="avis")
    niveau = models.CharField("niveau", max_length=10, choices=NIVEAUX)
    favorable = models.BooleanField("favorable")
    commentaire = models.CharField("commentaire", max_length=300, blank=True)
    par = _compte(null=False)
    date = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "avis de mutation"
        verbose_name_plural = "avis de mutation"
        ordering = ["date", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["mutation", "niveau"], name="un_avis_par_niveau")
        ]

    def __str__(self) -> str:
        return f"{self.get_niveau_display()} : {'favorable' if self.favorable else 'défavorable'}"


class Signalement(models.Model):
    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="signalements")
    type = models.CharField("type", max_length=20, choices=TypeSignalement.choices)
    etat = models.CharField(
        "état", max_length=10, choices=EtatDemande.choices, default=EtatDemande.BN
    )
    date_effet = models.DateField("date", null=True, blank=True)
    reference = models.CharField("référence", max_length=120, blank=True)
    nouvelle_categorie = models.CharField(
        "nouvelle catégorie", max_length=20, blank=True, choices=Categorie.choices
    )
    commentaire = models.CharField("commentaire", max_length=300, blank=True)
    unite = models.CharField("unité qui signale", max_length=40)
    demande_par = _compte(verbose_name="demandé par", null=False)
    date_demande = models.DateTimeField("date de la demande", auto_now_add=True)
    decide_par = _compte(verbose_name="décidé par")
    date_decision = models.DateTimeField("date de la décision", null=True, blank=True)
    motif_refus = models.CharField("motif du refus", max_length=300, blank=True)

    class Meta:
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
        ordering = ["-date_demande", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["membre", "type"],
                condition=Q(etat="bn"),
                name="un_signalement_en_cours_par_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_type_display()} — {self.membre.matricule}"


class TypeSanction(models.TextChoices):
    AVERTISSEMENT_VERBAL = "avertissement_verbal", "Avertissement verbal"
    AVERTISSEMENT_ECRIT = "avertissement_ecrit", "Avertissement écrit"
    AMENDE = "amende", "Amende"
    BLAME = "blame", "Blâme écrit"
    SUSPENSION = "suspension", "Suspension temporaire de service"
    RETRAIT = "retrait", "Retrait temporaire de responsabilités"
    EXCLUSION_TEMPORAIRE = "exclusion_temporaire", "Exclusion temporaire"
    EXCLUSION_DEFINITIVE = "exclusion_definitive", "Exclusion définitive"
    AUTRE = "autre", "Autre"


EFFETS_SANCTION = {
    TypeSanction.SUSPENSION: Statut.SANCTIONNE,
    TypeSanction.RETRAIT: Statut.SANCTIONNE,
    TypeSanction.EXCLUSION_TEMPORAIRE: Statut.EXCLU,
    TypeSanction.EXCLUSION_DEFINITIVE: Statut.EXCLU,
}
SANCTIONS_TEMPORAIRES = (
    TypeSanction.SUSPENSION,
    TypeSanction.RETRAIT,
    TypeSanction.EXCLUSION_TEMPORAIRE,
)


class Sanction(models.Model):
    DEGRES = [(1, "1ᵉʳ degré"), (2, "2ᵉ degré"), (3, "3ᵉ degré")]

    membre = models.ForeignKey(Membre, on_delete=models.PROTECT, related_name="sanctions")
    degre = models.PositiveSmallIntegerField("degré de la faute", choices=DEGRES)
    type = models.CharField("type de sanction", max_length=30, choices=TypeSanction.choices)
    precision = models.CharField("précision", max_length=200, blank=True)
    date_debut = models.DateField("date de début")
    date_fin = models.DateField("date de fin", null=True, blank=True)
    motif = models.CharField("motif résumé", max_length=300)
    reference = models.CharField("référence de la décision", max_length=120)
    par = _compte(verbose_name="inscrite par")
    date = models.DateTimeField("inscrite le", auto_now_add=True)
    levee_le = models.DateField("levée le", null=True, blank=True)
    levee_par = _compte(verbose_name="levée par")
    motif_levee = models.CharField("motif de la levée", max_length=300, blank=True)

    class Meta:
        verbose_name = "sanction"
        verbose_name_plural = "sanctions"
        ordering = ["-date_debut", "-pk"]

    def __str__(self) -> str:
        return f"{self.get_type_display()} — {self.membre.matricule}"

    @property
    def effet(self) -> str | None:
        return EFFETS_SANCTION.get(self.type)

    @property
    def libelle(self) -> str:
        if self.type == TypeSanction.AUTRE and self.precision:
            return f"Autre : {self.precision}"
        return self.get_type_display()

    def en_cours(self, jour) -> bool:
        if self.levee_le is not None or self.date_debut > jour:
            return False
        return self.date_fin is None or jour < self.date_fin
