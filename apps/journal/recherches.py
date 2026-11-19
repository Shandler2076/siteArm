"""Recherches d'un membre par son matricule (« payer pour », aperçu de mutation) : chacune est
inscrite au journal, et leur nombre par jour est limité pour qu'on ne puisse pas parcourir les
matricules un à un (faille M3 de l'analyse du 19/11/2026)."""

from django.conf import settings
from django.utils import timezone

from apps.journal.models import RECHERCHE_MATRICULE, EntreeJournal
from apps.journal.services import journaliser

MESSAGE_LIMITE = (
    "Trop de recherches de matricules aujourd'hui. Réessayez demain, ou adressez-vous à votre "
    "paroisse."
)


def recherches_epuisees(compte) -> bool:
    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    faites = EntreeJournal.objects.filter(
        action=RECHERCHE_MATRICULE, auteur=compte, date__gte=debut
    ).count()
    return faites >= settings.LIMITE_RECHERCHES_MATRICULE


def noter_recherche(compte, *, pour: str, saisi: str, membre=None) -> None:
    journaliser(
        compte,
        RECHERCHE_MATRICULE,
        pour=pour,
        saisi=saisi[:40],
        membre=membre.matricule if membre else "",
    )
