"""Seuls points d'entrée qui changent le statut ou la catégorie d'un membre.

Chaque changement est inscrit dans l'historique du membre ; le compte suit le statut.
"""

import calendar
import datetime

from django.db import transaction
from django.db.models import Q

from apps.bureaux.models import Mandat
from apps.membres.models import Statut
from apps.mouvements.models import HistoriqueMembre, TypeHistorique

STATUTS_AVEC_ACCES = (Statut.ACTIF, Statut.SANCTIONNE)
STATUTS_SORTIE = (Statut.DECEDE, Statut.DEMISSIONNAIRE, Statut.EXCLU)


def ajouter_mois(jour: datetime.date, mois: int) -> datetime.date:
    total = jour.month - 1 + mois
    annee, mois_final = jour.year + total // 12, total % 12 + 1
    dernier = calendar.monthrange(annee, mois_final)[1]
    return datetime.date(annee, mois_final, min(jour.day, dernier))


def clore_mandats(membre, jour: datetime.date, unites: set | None = None) -> list[Mandat]:
    """Clôt les mandats en cours (ou à venir) ; `unites` limite aux mandats de ces unités."""
    mandats = membre.mandats.filter(Q(date_fin__isnull=True) | Q(date_fin__gt=jour))
    clos = []
    for m in mandats.select_related("fonction", "paroisse", "circuit", "region"):
        if unites is not None and m.unite not in unites:
            continue
        m.date_fin = max(jour, m.date_debut)
        m.save(update_fields=["date_fin"])
        clos.append(m)
    return clos


@transaction.atomic
def changer_statut(
    membre, nouveau: str, *, par, date_effet: datetime.date, motif: str, reference: str = ""
) -> HistoriqueMembre:
    ancien = membre.statut
    membre.statut = nouveau
    membre.save(update_fields=["statut"])
    if membre.compte_id:
        compte = membre.compte
        compte.is_active = nouveau in STATUTS_AVEC_ACCES
        compte.save(update_fields=["is_active"])
    if nouveau in STATUTS_SORTIE:
        clore_mandats(membre, date_effet)
    return HistoriqueMembre.objects.create(
        membre=membre,
        type=TypeHistorique.STATUT,
        ancien=ancien,
        nouveau=nouveau,
        date_effet=date_effet,
        motif=motif,
        reference=reference,
        par=par if getattr(par, "is_authenticated", False) else None,
    )


@transaction.atomic
def changer_categorie(
    membre, nouvelle: str, *, par, date_effet: datetime.date, motif: str, reference: str = ""
) -> HistoriqueMembre:
    ancienne = membre.categorie
    membre.categorie = nouvelle
    membre.save(update_fields=["categorie"])
    return HistoriqueMembre.objects.create(
        membre=membre,
        type=TypeHistorique.CATEGORIE,
        ancien=ancienne,
        nouveau=nouvelle,
        date_effet=date_effet,
        motif=motif,
        reference=reference,
        par=par if getattr(par, "is_authenticated", False) else None,
    )
