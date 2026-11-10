from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.comptes.managers import CompteManager


def normaliser_identifiant(valeur: str) -> str:
    """Identifiant sans espaces autour et en majuscules (ex. 2015-01AS-0157)."""
    return valeur.strip().upper()


class Compte(AbstractBaseUser, PermissionsMixin):
    identifiant = models.CharField("identifiant", max_length=20, unique=True)
    nom_affiche = models.CharField("nom affiché", max_length=150, blank=True)
    doit_changer_mot_de_passe = models.BooleanField(
        "doit changer son mot de passe", default=True
    )
    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField("accès à la gestion", default=False)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    objects = CompteManager()

    USERNAME_FIELD = "identifiant"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "compte"
        verbose_name_plural = "comptes"

    def __str__(self) -> str:
        return self.nom_affiche or self.identifiant
