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


class EntreeJournal(models.Model):
    date = models.DateTimeField("date", auto_now_add=True, db_index=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="auteur",
    )
    action = models.CharField("action", max_length=60, db_index=True)
    unite = models.CharField("unité", max_length=40, blank=True)
    details = models.JSONField("détails", default=dict, blank=True)

    class Meta:
        verbose_name = "entrée du journal"
        verbose_name_plural = "journal"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.date:%d/%m/%Y %H:%M} — {self.action}"
