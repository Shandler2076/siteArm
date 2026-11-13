"""Règles de calcul des cotisations (fonctions pures sur les données lues en base).

- Dû : chaque mois à partir du mois de départ (ou du mois d'enregistrement s'il est plus tardif)
  jusqu'au mois en cours, pour tous les membres, sauf les mois où la personne est exclue,
  démissionnaire ou décédée (statut au premier jour du mois).
- À jour : tous les mois dus sont payés ET validés.
"""

import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from apps.cotisations.models import (
    EtatVersement,
    MoisCotise,
    ParametresCotisations,
    premier_du_mois,
    tarif_parmi,
    tarifs,
)
from apps.membres.models import Statut

HORS_MOUVEMENT = {Statut.EXCLU, Statut.DEMISSIONNAIRE, Statut.DECEDE}


@dataclass
class Situation:
    dus: list = field(default_factory=list)
    payes: set = field(default_factory=set)
    en_attente: set = field(default_factory=set)
    retard: int = 0
    reste_du: int = 0
    a_jour: bool = True
    total_annee: int = 0
    total_depuis_debut: int = 0
    totaux_par_annee: dict = field(default_factory=dict)


def mois_suivant(mois: datetime.date) -> datetime.date:
    return (mois.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)


def _mois_entre(debut: datetime.date, fin: datetime.date) -> list[datetime.date]:
    resultat, m = [], debut
    while m <= fin:
        resultat.append(m)
        m = mois_suivant(m)
    return resultat


def _statut_au(changements: list, statut_actuel: str, jour: datetime.date) -> str:
    """`changements` : [(date_effet, ancien, nouveau)] triés ; sans changement : statut actuel."""
    if not changements:
        return statut_actuel
    statut = changements[0][1]
    for date_effet, _ancien, nouveau in changements:
        if date_effet <= jour:
            statut = nouveau
    return statut


def _dus(membre, changements, mois_depart, jusqu_a) -> list[datetime.date]:
    if mois_depart is None:
        return []
    debut = max(mois_depart, premier_du_mois(membre.date_enregistrement.date()))
    return [
        m
        for m in _mois_entre(debut, premier_du_mois(jusqu_a))
        if _statut_au(changements, membre.statut, m) not in HORS_MOUVEMENT
    ]


def _changements(membres) -> dict[int, list]:
    from apps.mouvements.models import HistoriqueMembre, TypeHistorique

    par_membre = defaultdict(list)
    lignes = (
        HistoriqueMembre.objects.filter(membre__in=membres, type=TypeHistorique.STATUT)
        .order_by("date_effet", "pk")
        .values_list("membre_id", "date_effet", "ancien", "nouveau")
    )
    for membre_id, date_effet, ancien, nouveau in lignes:
        par_membre[membre_id].append((date_effet, ancien, nouveau))
    return par_membre


def mois_dus(membre, jusqu_a: datetime.date) -> list[datetime.date]:
    mois_depart = ParametresCotisations.courant().mois_depart
    return _dus(membre, _changements([membre]).get(membre.pk, []), mois_depart, jusqu_a)


def _situation(dus, cotises, liste_tarifs, mois_courant) -> Situation:
    payes, en_attente = set(), set()
    total_annee = total = 0
    par_annee = defaultdict(int)
    for mois, montant, etat in cotises:
        if etat == EtatVersement.VALIDE:
            payes.add(mois)
            total += montant
            par_annee[mois.year] += montant
            if mois.year == mois_courant.year:
                total_annee += montant
        elif etat == EtatVersement.EN_ATTENTE:
            en_attente.add(mois)
    manquants = [m for m in dus if m not in payes]
    reste = sum(tarif_parmi(liste_tarifs, m).montant for m in manquants)
    return Situation(
        dus=dus,
        payes=payes,
        en_attente=en_attente,
        retard=len(manquants),
        reste_du=reste,
        a_jour=not manquants,
        total_annee=total_annee,
        total_depuis_debut=total,
        totaux_par_annee=dict(par_annee),
    )


def situations(qs, mois_courant: datetime.date) -> dict[int, Situation]:
    """Situation de chaque membre de `qs` au mois `mois_courant`, en quelques requêtes."""
    mois_courant = premier_du_mois(mois_courant)
    membres = list(qs.only("pk", "statut", "date_enregistrement"))
    mois_depart = ParametresCotisations.courant().mois_depart
    liste_tarifs = tarifs()
    changements = _changements(membres)
    cotises = defaultdict(list)
    for membre_id, mois, montant, etat in MoisCotise.objects.filter(
        membre__in=membres, actif=True
    ).values_list("membre_id", "mois", "montant", "versement__etat"):
        cotises[membre_id].append((mois, montant, etat))
    return {
        m.pk: _situation(
            _dus(m, changements.get(m.pk, []), mois_depart, mois_courant),
            cotises[m.pk],
            liste_tarifs,
            mois_courant,
        )
        for m in membres
    }


def situation(membre, mois_courant: datetime.date) -> Situation:
    from apps.membres.models import Membre

    return situations(Membre.objects.filter(pk=membre.pk), mois_courant)[membre.pk]


def annees_consultables(membre, s: Situation, annee_courante: int) -> list[int]:
    """Années que l'on peut afficher : du début des cotisations du membre à l'année en cours.

    Début = le plus tardif entre le départ des cotisations sur le site et l'enregistrement du
    membre. Une année où un mois a été payé d'avance s'ajoute aussi.
    """
    debut = annee_courante
    mois_depart = ParametresCotisations.courant().mois_depart
    if mois_depart is not None:
        inscrit = premier_du_mois(membre.date_enregistrement.date())
        debut = min(debut, max(mois_depart, inscrit).year)
    annees = set(range(debut, annee_courante + 1))
    annees |= {m.year for m in s.payes | s.en_attente}
    return sorted(annees)


def choisir_annee(valeur, annees: list[int], defaut: int) -> int:
    """Année demandée dans l'adresse (`?annee=`), sinon l'année en cours."""
    try:
        annee = int(valeur)
    except (TypeError, ValueError):
        return defaut
    return annee if annee in annees else defaut


def cases_annee(s: Situation, annee: int) -> list[dict]:
    """Les 12 mois de `annee` : payé, en attente, dû ou non dû."""
    from apps.cotisations.services import MOIS

    cases = []
    for i, nom in enumerate(MOIS):
        mo = datetime.date(annee, i + 1, 1)
        if mo in s.payes:
            etat = "paye"
        elif mo in s.en_attente:
            etat = "attente"
        elif mo in s.dus:
            etat = "du"
        else:
            etat = "non_du"
        cases.append({"nom": nom.capitalize(), "etat": etat})
    return cases
