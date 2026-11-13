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


# --- Catégories (décision du 13/11/2026) ----------------------------------------------------------


class CategorieRefusee(Exception):
    """Changement de catégorie refusé ; le message s'affiche tel quel."""


def admettre_comme_actif(
    membre, *, date_effet: datetime.date, reference: str, motif: str, par
) -> HistoriqueMembre:
    """Seul passage prévu : sympathisant → membre actif, par décision du BNC."""
    from django.db import transaction

    from apps.journal.models import CATEGORIE as J_CATEGORIE
    from apps.journal.services import journaliser
    from apps.membres.models import Categorie, Membre
    from apps.notifications.services import notifier

    reference = (reference or "").strip()
    if not reference:
        raise CategorieRefusee("La référence de la décision du BNC est obligatoire.")
    with transaction.atomic():
        m = Membre.objects.select_for_update(of=("self",)).get(pk=membre.pk)
        if m.categorie != Categorie.SYMPATHISANT:
            raise CategorieRefusee(
                "Seul un membre sympathisant peut être admis comme membre actif."
            )
        h = changer_categorie(
            m,
            Categorie.ACTIF,
            par=par,
            date_effet=date_effet,
            motif=(motif or "").strip() or "Admission comme membre actif (décision du BNC)",
            reference=reference,
        )
        journaliser(
            par,
            J_CATEGORIE,
            unite="national",
            membre=m.matricule,
            ancien="sympathisant",
            nouveau="actif",
            reference=reference,
        )
        compte = m.compte
        texte = (
            f"Décision du BNC ({reference}) : vous êtes admis(e) comme membre actif "
            f"à compter du {date_effet:%d/%m/%Y}."
        )
        transaction.on_commit(lambda: notifier([compte], texte, "/membres/ma-fiche/"))
    return h


def corriger_categorie(membre, *, nouvelle: str, motif: str, par) -> HistoriqueMembre:
    """Erreur de saisie : correction par le BN seulement, motif obligatoire, journalisée."""
    from django.db import transaction
    from django.utils import timezone

    from apps.journal.models import CATEGORIE as J_CATEGORIE
    from apps.journal.services import journaliser
    from apps.membres.models import Categorie, Membre

    motif = (motif or "").strip()
    if not motif:
        raise CategorieRefusee("Le motif de la correction est obligatoire.")
    if nouvelle not in Categorie.values:
        raise CategorieRefusee("Catégorie inconnue.")
    with transaction.atomic():
        m = Membre.objects.select_for_update(of=("self",)).get(pk=membre.pk)
        if m.categorie == nouvelle:
            raise CategorieRefusee("C'est déjà la catégorie du membre.")
        ancienne = m.categorie
        h = changer_categorie(
            m, nouvelle, par=par, date_effet=timezone.localdate(), motif=f"Correction : {motif}"
        )
        journaliser(
            par,
            J_CATEGORIE,
            unite="national",
            membre=m.matricule,
            ancien=ancienne,
            nouveau=nouvelle,
            correction=True,
        )
    return h
