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
    EXCEPTIONNELLE = "exceptionnelle", "Promotion exceptionnelle"
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

    class Meta:
        verbose_name = "grade (historique)"
        verbose_name_plural = "grades (historique)"
        ordering = ["date_effet", "date_saisie"]

    def __str__(self) -> str:
        return f"{self.get_grade_display()} — {self.date_effet:%d/%m/%Y}"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("On ne supprime pas un grade : on le corrige.")
