"""Historique des grades d'un membre. Seul `apps/grades/services.py` y écrit."""

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models

from apps.membres.grades import Grade


class ModeGrade(models.TextChoices):
    ENTREE = "entree", "Entrée dans le mouvement"
    PREMIERE_CONSECRATION = "premiere_consecration", "Première consécration"
    REGULARISATION = "regularisation", "Régularisation"
    TEST = "test", "Test"
    NOMINATION = "nomination", "Nomination"
    EXCEPTIONNELLE = "exceptionnelle", "Promotion spéciale (art. 84)"
    CORRECTION = "correction", "Correction"


class HistoriqueGrade(models.Model):
    membre = models.ForeignKey(
        "membres.Membre", on_delete=models.PROTECT, related_name="grades", verbose_name="membre"
    )
    grade = models.PositiveSmallIntegerField("grade", choices=Grade.choices)
    date_effet = models.DateField("date d'effet")
    mode = models.CharField("mode", max_length=30, choices=ModeGrade.choices)
    reference = models.CharField("référence de la décision", max_length=200, blank=True)
    motif = models.TextField("motif", blank=True)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="enregistré par",
    )
    date_saisie = models.DateTimeField("saisi le", auto_now_add=True)
    acte = models.ForeignKey(
        "ActePromotion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promotions",
        verbose_name="acte de promotion",
    )

    class Meta:
        verbose_name = "grade (historique)"
        verbose_name_plural = "grades (historique)"
        ordering = ["date_effet", "date_saisie"]

    def __str__(self) -> str:
        return f"{self.get_grade_display()} — {self.date_effet:%d/%m/%Y}"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("On ne supprime pas un grade : on le corrige.")


# --- Sessions de test ou d'examen, actes de promotion (décisions du 13/11/2026) ------------------


class TypeEpreuve(models.TextChoices):
    TEST = "test", "Test"
    EXAMEN = "examen", "Examen"


class NatureActe(models.TextChoices):
    EPREUVE = "epreuve", "Promotion après test ou examen"
    SPECIALE = "speciale", "Promotion spéciale (art. 84)"


class ActePromotion(models.Model):
    """Décision du BNC portant promotion ; l'acte PDF est généré à partir de cette fiche."""

    numero = models.CharField("numéro de la décision", max_length=50)
    date_decision = models.DateField("date de la décision")
    nature = models.CharField("nature", max_length=10, choices=NatureActe.choices)
    date_effet = models.DateField("date d'effet")
    motif = models.TextField("motif (promotion spéciale)", blank=True)
    signataire = models.CharField("Président (signataire)", max_length=200, blank=True)
    session = models.ForeignKey(
        "SessionEpreuve",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="actes",
        verbose_name="session de test ou d'examen",
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    date_creation = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "acte de promotion"
        verbose_name_plural = "actes de promotion"
        ordering = ["-date_decision", "-pk"]

    def __str__(self) -> str:
        return f"Décision n° {self.numero} du {self.date_decision:%d/%m/%Y}"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Un acte de promotion ne se supprime pas.")


class SessionEpreuve(models.Model):
    type = models.CharField("type d'épreuve", max_length=10, choices=TypeEpreuve.choices)
    date = models.DateField("date de l'épreuve")
    lieu = models.CharField("lieu", max_length=200, blank=True)
    grade_vise = models.PositiveSmallIntegerField("grade visé", choices=Grade.choices)
    acte = models.ForeignKey(
        ActePromotion, on_delete=models.PROTECT, null=True, blank=True, related_name="sessions"
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    date_creation = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "session de test ou d'examen"
        verbose_name_plural = "sessions de test ou d'examen"
        ordering = ["-date", "-pk"]

    def __str__(self) -> str:
        return (
            f"{self.get_type_display()} du {self.date:%d/%m/%Y} — {self.get_grade_vise_display()}"
        )

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Une session ne se supprime pas.")


class Resultat(models.TextChoices):
    NON_SAISI = "", "Non saisi"
    ADMIS = "admis", "Admis"
    AJOURNE = "ajourne", "Ajourné"
    ABSENT = "absent", "Absent"


class Candidat(models.Model):
    session = models.ForeignKey(SessionEpreuve, on_delete=models.PROTECT, related_name="candidats")
    membre = models.ForeignKey("membres.Membre", on_delete=models.PROTECT, related_name="+")
    resultat = models.CharField(
        "résultat", max_length=10, choices=Resultat.choices, default="", blank=True
    )
    promu = models.BooleanField("promu", default=False)

    class Meta:
        verbose_name = "candidat"
        ordering = ["membre__nom", "membre__prenoms"]
        constraints = [
            models.UniqueConstraint(fields=["session", "membre"], name="candidat_unique")
        ]

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Un candidat ne se supprime pas.")
