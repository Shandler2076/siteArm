"""Journal des actions (minimal à l'étape 5 ; complété à l'étape 7)."""

from django.conf import settings
from django.db import models

LISTE_PDF = "liste_pdf"
LISTE_EXCEL = "liste_excel"
STATISTIQUES_PDF = "statistiques_pdf"
TRANCHES_AGE = "tranches_age"
MUTATION_DEMANDEE = "mutation_demandee"
MUTATION_AVIS = "mutation_avis"
MUTATION_DECIDEE = "mutation_decidee"
SIGNALEMENT = "signalement"
SIGNALEMENT_DECIDE = "signalement_decide"
CONNEXION = "connexion"
CONNEXION_ECHOUEE = "connexion_echouee"
CONSULTATION_FICHE = "consultation_fiche"
VERIFICATION_MEMBRE = "verification_membre"
REINITIALISATION = "reinitialisation"
PHOTO_DECISION = "photo_decision"
ENREGISTREMENT = "enregistrement"
LOT_VALIDE = "lot_valide"
INSTALLATION_BUREAU = "installation_bureau"
COORDONNEES = "coordonnees"
SANCTION = "sanction"
SANCTION_LEVEE = "sanction_levee"
FIN_SANCTION = "fin_sanction"
CORRECTION_INTEGRATION = "correction_integration"
DOUBLE_VERIFICATION = "double_verification"
GRADE_ATTRIBUE = "grade_attribue"
GRADE_PROMOTION = "grade_promotion"
GRADE_CORRECTION = "grade_correction"
VERSEMENT_SAISI = "versement_saisi"
VERSEMENT_VALIDE = "versement_valide"
VERSEMENT_REFUSE = "versement_refuse"
VERSEMENT_ANNULE = "versement_annule"
PART_RECUE = "part_recue"
REGLAGE_COTISATIONS = "reglage_cotisations"
EVENEMENT_CREE = "evenement_cree"
EVENEMENT_MODIFIE = "evenement_modifie"
EVENEMENT_ANNULE = "evenement_annule"
CONVOCATION = "convocation"
CONVOCATION_RETIREE = "convocation_retiree"
PRESENCE = "presence"
VERSEMENT_MOBILE_MONEY = "versement_mobile_money"
COTISATION_SPECIALE = "cotisation_speciale"
CONTRIBUTION = "contribution"
PAIEMENT_ECHOUE = "paiement_echoue"
NUMERO_TRESORIER = "numero_tresorier"
REVERSEMENTS_PREPARES = "reversements_prepares"
REVERSEMENTS_VALIDES = "reversements_valides"
REVERSEMENT_ENVOYE = "reversement_envoye"

LIBELLES = {
    VERSEMENT_MOBILE_MONEY: "Cotisation payée par mobile money",
    COTISATION_SPECIALE: "Cotisation spéciale créée",
    CONTRIBUTION: "Cotisation spéciale payée",
    PAIEMENT_ECHOUE: "Paiement mobile money échoué",
    NUMERO_TRESORIER: "Numéro mobile money d'un bureau",
    REVERSEMENTS_PREPARES: "Reversements préparés",
    REVERSEMENTS_VALIDES: "Reversements validés",
    REVERSEMENT_ENVOYE: "Reversement envoyé",
    LISTE_PDF: "Liste téléchargée (PDF)",
    LISTE_EXCEL: "Liste téléchargée (Excel)",
    STATISTIQUES_PDF: "Statistiques téléchargées (PDF)",
    TRANCHES_AGE: "Tranches d'âge modifiées",
    MUTATION_DEMANDEE: "Mutation demandée",
    MUTATION_AVIS: "Avis de mutation",
    MUTATION_DECIDEE: "Mutation décidée",
    SIGNALEMENT: "Signalement",
    SIGNALEMENT_DECIDE: "Signalement décidé",
    CONNEXION: "Connexion",
    CONNEXION_ECHOUEE: "Connexion échouée",
    CONSULTATION_FICHE: "Consultation d'une fiche",
    VERIFICATION_MEMBRE: "Vérification d'un membre (hors périmètre)",
    REINITIALISATION: "Mot de passe réinitialisé",
    PHOTO_DECISION: "Décision sur une photo",
    ENREGISTREMENT: "Membre enregistré",
    LOT_VALIDE: "Lot validé",
    INSTALLATION_BUREAU: "Bureau installé",
    COORDONNEES: "Coordonnées modifiées",
    SANCTION: "Sanction inscrite",
    SANCTION_LEVEE: "Sanction levée",
    FIN_SANCTION: "Fin de sanction",
    CORRECTION_INTEGRATION: "Correction exceptionnelle",
    DOUBLE_VERIFICATION: "Double vérification",
    GRADE_ATTRIBUE: "Grade attribué",
    GRADE_PROMOTION: "Promotion de grade",
    GRADE_CORRECTION: "Correction de grade",
    VERSEMENT_SAISI: "Cotisation : versement enregistré",
    VERSEMENT_VALIDE: "Cotisation : versement validé",
    VERSEMENT_REFUSE: "Cotisation : versement refusé",
    VERSEMENT_ANNULE: "Cotisation : versement annulé",
    PART_RECUE: "Cotisation : part reçue",
    REGLAGE_COTISATIONS: "Cotisations : réglages modifiés",
    EVENEMENT_CREE: "Événement créé",
    EVENEMENT_MODIFIE: "Événement modifié",
    EVENEMENT_ANNULE: "Événement annulé",
    CONVOCATION: "Convocation",
    CONVOCATION_RETIREE: "Convocation retirée",
    PRESENCE: "Présence pointée",
}


class JournalImmuable(Exception):
    """Le journal ne se modifie pas et ne s'efface pas."""


class JournalQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise JournalImmuable("Le journal ne peut pas être modifié.")

    def delete(self):
        raise JournalImmuable("Le journal ne peut pas être effacé.")


class EntreeJournal(models.Model):
    date = models.DateTimeField("date", auto_now_add=True, db_index=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,  # un compte cité au journal ne se supprime pas
        related_name="+",
        verbose_name="auteur",
    )
    auteur_identifiant = models.CharField("identifiant de l'auteur", max_length=150, blank=True)
    action = models.CharField("action", max_length=60, db_index=True)
    unite = models.CharField("unité", max_length=40, blank=True)
    details = models.JSONField("détails", default=dict, blank=True)

    objects = JournalQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée du journal"
        verbose_name_plural = "journal"
        ordering = ["-date"]
        base_manager_name = "objects"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise JournalImmuable("Le journal ne peut pas être modifié.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise JournalImmuable("Le journal ne peut pas être effacé.")

    @property
    def libelle(self) -> str:
        return LIBELLES.get(self.action, self.action)

    def __str__(self) -> str:
        return f"{self.date:%d/%m/%Y %H:%M} — {self.action}"
