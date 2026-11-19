"""Décision du 19/11/2026 : « passés » = événements réellement tenus (convocations envoyées) ;
« annulés » = annulés après envoi des convocations ; les autres sont « non aboutis »."""

import datetime

from django.utils import timezone

from apps.evenements.models import Evenement
from apps.evenements.services import convoquer, creer_evenement


def _ev(compte, nom, jours):
    return creer_evenement(
        nom=nom, debut=timezone.now() + datetime.timedelta(days=jours), par=compte
    )


def test_passes_seulement_les_evenements_tenus(monde, compte_technique, client_technique):
    tenu = _ev(compte_technique, "Tenu", -10)
    convoquer(tenu, [monde["m1"]], par=compte_technique)
    _ev(compte_technique, "Jamais convoqué", -5)
    annule_vide = _ev(compte_technique, "Annulé sans convocation", -3)
    Evenement.objects.filter(pk=annule_vide.pk).update(etat="annule", motif_annulation="x")
    annule = _ev(compte_technique, "Annulé après convocation", 2)
    convoquer(annule, [monde["m2"]], par=compte_technique)
    Evenement.objects.filter(pk=annule.pk).update(etat="annule", motif_annulation="pluie")
    r = client_technique.get("/evenements/")
    ctx = r.context
    assert [e.nom for e in ctx["passes"]] == ["Tenu"]
    assert [e.nom for e in ctx["annules"]] == ["Annulé après convocation"]
    assert {e.nom for e in ctx["non_aboutis"]} == {"Jamais convoqué", "Annulé sans convocation"}
