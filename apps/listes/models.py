from django.db import models

BORNES_PAR_DEFAUT = "18,40"


class ReglageStatistiques(models.Model):
    """Réglage unique (pk=1) : bornes des tranches d'âge, modifiables par le BN."""

    bornes = models.CharField("bornes des tranches d'âge", max_length=60, default=BORNES_PAR_DEFAUT)

    class Meta:
        verbose_name = "réglage des statistiques"
        verbose_name_plural = "réglages des statistiques"

    def __str__(self) -> str:
        return f"Tranches d'âge : {self.bornes}"

    @classmethod
    def courant(cls) -> "ReglageStatistiques":
        return cls.objects.get_or_create(pk=1)[0]

    @property
    def liste_bornes(self) -> list[int]:
        return [int(b) for b in self.bornes.split(",") if b.strip()]
