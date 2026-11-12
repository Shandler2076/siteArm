"""Fiche d'un membre en rubriques : Profil, Cotisation mensuelle, Participation aux événements.

Les événements ne sont visibles que du Bureau national (décision du 12/11/2026).
"""

import datetime

from django.utils import timezone

RUBRIQUES = [
    ("profil", "Profil"),
    ("cotisations", "Cotisation mensuelle"),
    ("evenements", "Participation aux événements"),
]


def contexte_rubriques(request, membre, avec_evenements: bool) -> dict:
    possibles = [r for r in RUBRIQUES if avec_evenements or r[0] != "evenements"]
    rubrique = request.GET.get("rubrique", "profil")
    if rubrique not in {cle for cle, _ in possibles}:
        rubrique = "profil"
    ctx = {"rubriques": possibles, "rubrique": rubrique}
    if rubrique == "cotisations":
        ctx.update(_cotisations(membre))
    elif rubrique == "evenements":
        ctx["convocations"] = membre.convocations.select_related("evenement", "session").order_by(
            "-evenement__debut"
        )
    return ctx


def _cotisations(membre) -> dict:
    from apps.cotisations.models import EtatVersement
    from apps.cotisations.regles import situation
    from apps.cotisations.services import MOIS

    jour = timezone.localdate()
    mois_courant = jour.replace(day=1)
    s = situation(membre, mois_courant)
    cases = []
    for i, nom in enumerate(MOIS):
        mo = datetime.date(jour.year, i + 1, 1)
        if mo in s.payes:
            etat = "paye"
        elif mo in s.en_attente:
            etat = "attente"
        elif mo in s.dus:
            etat = "du"
        else:
            etat = "non_du"
        cases.append({"nom": nom.capitalize(), "etat": etat})
    return {
        "cot_situation": s,
        "cot_cases": cases,
        "cot_annee": jour.year,
        "cot_mois": mois_courant,
        "cot_versements": membre.versements.exclude(etat=EtatVersement.ANNULE)
        .select_related("paroisse")
        .prefetch_related("mois")[:50],
    }
