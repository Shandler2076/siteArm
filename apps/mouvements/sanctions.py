"""Sanctions (§6.4) : seul le BNC les inscrit ; elles passent par `changer_statut`."""

import datetime

from django.db import transaction
from django.utils import timezone

from apps.journal import models as journal
from apps.journal.services import journaliser
from apps.membres.models import Statut
from apps.mouvements.models import (
    EFFETS_SANCTION,
    SANCTIONS_TEMPORAIRES,
    Sanction,
    TypeHistorique,
    TypeSanction,
)
from apps.mouvements.services import (
    MouvementRefuse,
    _annuler_mutations,
    _unites_du_membre,
    _verrouiller_membre,
    notifier_unites,
)
from apps.mouvements.statuts import changer_statut

GRAVITE = {Statut.ACTIF: 0, Statut.SANCTIONNE: 1, Statut.EXCLU: 2}
MOTIF_DEBUT = "Début de la sanction"
MOTIF_FIN = "Fin de la sanction"
MOTIF_LEVEE = "Sanction levée"
DUREE_MAX_SUSPENSION = 15


def statut_requis(membre, jour: datetime.date) -> str:
    """Statut imposé par les sanctions en cours (le plus grave), sinon « Actif »."""
    requis = Statut.ACTIF
    for s in membre.sanctions.filter(type__in=list(EFFETS_SANCTION), levee_le__isnull=True):
        if s.en_cours(jour) and GRAVITE[s.effet] > GRAVITE[requis]:
            requis = s.effet
    return requis


def _statut_du_aux_sanctions(membre) -> bool:
    """Le statut actuel a-t-il été posé par une sanction ? (jamais un statut posé autrement)"""
    dernier = (
        membre.historique.filter(type=TypeHistorique.STATUT).order_by("-date_effet", "-pk").first()
    )
    return dernier is not None and (
        dernier.motif.startswith("Sanction") or dernier.motif in (MOTIF_DEBUT, MOTIF_FIN)
    )


def _ajuster_statut(membre, jour, *, par, motif_hausse, motif_baisse, reference="") -> int:
    """Aligne le statut sur les sanctions : +1 si aggravé, -1 si allégé, 0 sinon."""
    if membre.statut not in GRAVITE:
        return 0
    requis = statut_requis(membre, jour)
    if GRAVITE[requis] > GRAVITE[membre.statut]:
        changer_statut(
            membre, requis, par=par, date_effet=jour, motif=motif_hausse, reference=reference
        )
        if requis == Statut.EXCLU:
            _annuler_mutations(membre, "Annulée : exclusion")
        return 1
    if GRAVITE[requis] < GRAVITE[membre.statut] and _statut_du_aux_sanctions(membre):
        changer_statut(membre, requis, par=par, date_effet=jour, motif=motif_baisse)
        return -1
    return 0


def _verifier(membre, degre, type_, date_debut, date_fin, precision) -> None:
    if type_ not in TypeSanction.values:
        raise MouvementRefuse("Type de sanction inconnu.")
    if degre not in (1, 2, 3):
        raise MouvementRefuse("Le degré de la faute doit être 1, 2 ou 3.")
    if membre.statut in (Statut.DECEDE, Statut.DEMISSIONNAIRE):
        raise MouvementRefuse("Impossible de sanctionner un membre décédé ou démissionnaire.")
    if membre.sanctions.filter(
        type=TypeSanction.EXCLUSION_DEFINITIVE, levee_le__isnull=True
    ).exists():
        raise MouvementRefuse("Ce membre est déjà exclu définitivement.")
    if type_ == TypeSanction.AUTRE and not precision.strip():
        raise MouvementRefuse("Précisez la sanction (type « Autre »).")
    if date_debut is None:
        raise MouvementRefuse("Indiquez la date de début.")
    if type_ == TypeSanction.EXCLUSION_DEFINITIVE and date_fin is not None:
        raise MouvementRefuse("Une exclusion définitive n'a pas de date de fin.")
    if type_ in SANCTIONS_TEMPORAIRES and date_fin is None:
        raise MouvementRefuse("Indiquez la date de fin de cette sanction temporaire.")
    if date_fin is not None and date_fin <= date_debut:
        raise MouvementRefuse("La date de fin ne peut pas précéder la date de début.")
    if type_ == TypeSanction.SUSPENSION and (date_fin - date_debut).days > DUREE_MAX_SUSPENSION:
        raise MouvementRefuse("Une suspension temporaire dure 15 jours au plus (RI art. 156).")


def _message(sanction: Sanction, debut: str) -> str:
    m = sanction.membre
    return f"{debut} : {sanction.libelle} — {m.matricule} {m.nom_complet}"


def enregistrer_sanction(
    *,
    membre,
    degre: int,
    type: str,  # noqa: A002 — nom métier
    date_debut: datetime.date,
    motif: str,
    reference: str,
    par,
    date_fin: datetime.date | None = None,
    precision: str = "",
    jour: datetime.date | None = None,
) -> Sanction:
    jour = jour or timezone.localdate()
    with transaction.atomic():
        membre = _verrouiller_membre(membre.pk)
        _verifier(membre, degre, type, date_debut, date_fin, precision)
        sanction = Sanction.objects.create(
            membre=membre,
            degre=degre,
            type=type,
            precision=precision.strip(),
            date_debut=date_debut,
            date_fin=date_fin,
            motif=motif,
            reference=reference,
            par=par,
        )
        _ajuster_statut(
            membre,
            jour,
            par=par,
            motif_hausse=f"Sanction : {sanction.libelle}",
            motif_baisse=MOTIF_FIN,
            reference=reference,
        )
    journaliser(
        par,
        journal.SANCTION,
        membre=membre.matricule,
        type=type,
        degre=degre,
        date_debut=date_debut.isoformat(),
        date_fin=date_fin.isoformat() if date_fin else None,
        reference=reference,
    )
    notifier_unites(
        _unites_du_membre(membre), _message(sanction, "Sanction inscrite"), comptes=[membre.compte]
    )
    return sanction


def lever_sanction(*, sanction, motif: str, par, jour: datetime.date | None = None) -> Sanction:
    jour = jour or timezone.localdate()
    if not motif.strip():
        raise MouvementRefuse("Indiquez le motif de la levée.")
    with transaction.atomic():
        membre = _verrouiller_membre(sanction.membre_id)
        sanction = Sanction.objects.select_for_update().get(pk=sanction.pk)
        if sanction.levee_le is not None:
            raise MouvementRefuse("Cette sanction est déjà levée.")
        sanction.levee_le, sanction.levee_par, sanction.motif_levee = jour, par, motif.strip()
        sanction.save(update_fields=["levee_le", "levee_par", "motif_levee"])
        _ajuster_statut(membre, jour, par=par, motif_hausse=MOTIF_DEBUT, motif_baisse=MOTIF_LEVEE)
    sanction.membre = membre
    journaliser(
        par,
        journal.SANCTION_LEVEE,
        membre=membre.matricule,
        sanction=sanction.pk,
        motif=sanction.motif_levee,
    )
    notifier_unites(
        _unites_du_membre(membre), _message(sanction, "Sanction levée"), comptes=[membre.compte]
    )
    return sanction


def appliquer_sanctions(jour: datetime.date | None = None) -> tuple[int, int]:
    """Tâche quotidienne : début des sanctions datées et fin des sanctions temporaires."""
    jour = jour or timezone.localdate()
    debuts = fins = 0
    membres = (
        Sanction.objects.filter(type__in=list(EFFETS_SANCTION))
        .values_list("membre_id", flat=True)
        .distinct()
    )
    for pk in membres:
        with transaction.atomic():
            membre = _verrouiller_membre(pk)
            avant = membre.statut
            sens = _ajuster_statut(
                membre, jour, par=None, motif_hausse=MOTIF_DEBUT, motif_baisse=MOTIF_FIN
            )
        if sens:
            debuts += sens > 0
            fins += sens < 0
            journaliser(
                None,
                journal.FIN_SANCTION if sens < 0 else journal.SANCTION,
                membre=membre.matricule,
                avant=avant,
                apres=membre.statut,
            )
            texte = "Fin de la sanction" if sens < 0 else "Début de la sanction"
            notifier_unites(
                _unites_du_membre(membre),
                f"{texte} : {membre.matricule} {membre.nom_complet}",
                comptes=[membre.compte],
            )
    return debuts, fins
