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
    faites = EntreeJournal.objects.filter(
        action=RECHERCHE_MATRICULE, auteur=compte, date__gte=_debut_du_jour()
    ).count()
    return faites >= settings.LIMITE_RECHERCHES_MATRICULE


def _cle(saisi: str) -> str:
    return (saisi or "").strip().upper()[:40]


def _debut_du_jour():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def deja_cherche(compte, *, pour: str, saisi: str) -> bool:
    """Ce matricule a déjà été cherché aujourd'hui, pour le même usage, par ce compte."""
    return EntreeJournal.objects.filter(
        action=RECHERCHE_MATRICULE,
        auteur=compte,
        date__gte=_debut_du_jour(),
        details__pour=pour,
        details__saisi=_cle(saisi),
    ).exists()


def noter_recherche(compte, *, pour: str, saisi: str, membre=None) -> None:
    journaliser(
        compte,
        RECHERCHE_MATRICULE,
        pour=pour,
        saisi=_cle(saisi),
        membre=membre.matricule if membre else "",
    )


def chercher(compte, *, pour: str, saisi: str, trouver, illimite: bool = False):
    """Point d'entrée unique d'une recherche par matricule. Renvoie (membre ou None, refusée).

    Toute requête qui révèle quelque chose (aperçu ET confirmation) passe par ici : un matricule
    déjà cherché aujourd'hui ne recompte pas (confirmer, recharger la page) ; sinon la recherche
    est comptée et inscrite au journal, et refusée au-delà de la limite du jour."""
    if deja_cherche(compte, pour=pour, saisi=saisi):
        return trouver(saisi), False
    if not illimite and recherches_epuisees(compte):
        return None, True
    membre = trouver(saisi)
    noter_recherche(compte, pour=pour, saisi=saisi, membre=membre)
    return membre, False
