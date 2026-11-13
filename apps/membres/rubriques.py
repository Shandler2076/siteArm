"""Fiche d'un membre en rubriques : Profil, Cotisation mensuelle, Participation aux événements.

Les événements ne sont visibles que du Bureau national (décision du 12/11/2026).
"""

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
        ctx.update(_cotisations(request, membre))
    elif rubrique == "evenements":
        ctx["convocations"] = membre.convocations.select_related("evenement", "session").order_by(
            "-evenement__debut"
        )
    return ctx


def _cotisations(request, membre) -> dict:
    from apps.cotisations.models import EtatVersement
    from apps.cotisations.regles import annees_consultables, cases_annee, choisir_annee, situation

    jour = timezone.localdate()
    mois_courant = jour.replace(day=1)
    s = situation(membre, mois_courant)
    annees = annees_consultables(membre, s, jour.year)
    annee = choisir_annee(request.GET.get("annee"), annees, jour.year)
    return {
        "cot_situation": s,
        "cot_cases": cases_annee(s, annee),
        "cot_annee": annee,
        "cot_annees": annees,
        "cot_total_annee": s.totaux_par_annee.get(annee, 0),
        "cot_mois": mois_courant,
        "cot_versements": membre.versements.exclude(etat=EtatVersement.ANNULE)
        .select_related("paroisse")
        .prefetch_related("mois")[:50],
    }
