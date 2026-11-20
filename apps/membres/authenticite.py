"""Authenticité de la fiche d'identification (décision du 20/11/2026).

On ne peut pas empêcher de recopier un PDF ; on rend une fausse fiche repérable en quelques
secondes. Chaque fiche imprimée est inscrite au registre (`FicheEmise`) avec un numéro, une
date d'émission et un jeton secret (code QR) ; la page publique `/membres/verifier/<jeton>/`
répond « authentique » ou « non valable », avec le STRICT MINIMUM : matricule, statut, numéro et
date d'émission (ni le nom, ni la photo, ni le téléphone, ni la date de naissance).
Une réimpression remplace les fiches précédentes du membre : elles deviennent non valables.
"""

import re
import secrets

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.membres.models import FicheEmise, Membre, Statut

JETON = re.compile(r"^[A-Za-z0-9_-]{32,64}$")


def emettre_fiche(membre: Membre, par=None) -> FicheEmise:
    """Inscrit une nouvelle fiche au registre et remplace les précédentes (tout ou rien)."""
    maintenant = timezone.now()
    with transaction.atomic():
        Membre.objects.select_for_update().filter(pk=membre.pk).first()  # une émission à la fois
        FicheEmise.objects.filter(membre=membre, remplacee_le__isnull=True).update(
            remplacee_le=maintenant
        )
        fiche = FicheEmise.objects.create(
            membre=membre,
            jeton=secrets.token_urlsafe(32),
            emise_le=maintenant,
            emise_par=par if getattr(par, "pk", None) else None,
        )
        fiche.numero = f"FI-{timezone.localtime(maintenant).year}-{fiche.pk:06d}"
        fiche.save(update_fields=["numero"])
    return fiche


def fiche_par_jeton(jeton: str) -> FicheEmise | None:
    if not jeton or not JETON.match(jeton):
        return None
    return FicheEmise.objects.select_related("membre").filter(jeton=jeton).first()


def etat_fiche(fiche: FicheEmise | None) -> tuple[str, str]:
    """(« authentique » | « remplacee » | « inconnue », explication en clair)."""
    if fiche is None:
        return (
            "inconnue",
            "Aucune fiche ne correspond à ce code : la fiche est fausse ou a été mal recopiée.",
        )
    if fiche.remplacee_le is not None:
        quand = timezone.localtime(fiche.remplacee_le)
        return (
            "remplacee",
            f"Cette fiche a été remplacée le {quand:%d/%m/%Y} par une fiche plus récente : "
            "elle n'est plus valable.",
        )
    if fiche.membre.statut != Statut.ACTIF:
        return (
            "authentique",
            f"Fiche émise par le site, mais le membre n'est plus actif : "
            f"{fiche.membre.get_statut_display()}.",
        )
    return "authentique", "Fiche émise par le site et toujours valable."


def url_verification(fiche: FicheEmise) -> str:
    chemin = reverse("membres:verifier", args=[fiche.jeton])
    return settings.SITE_URL.rstrip("/") + chemin
