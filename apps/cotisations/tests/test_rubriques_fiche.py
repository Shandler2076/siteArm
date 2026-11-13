"""Fiche d'un membre en rubriques : Profil, Cotisation mensuelle, Participation aux événements."""

import datetime
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone


def _html(c, url):
    r = c.get(url)
    assert r.status_code == 200, url
    return unescape(r.content.decode())


@pytest.fixture
def situe(monde, compte_technique):
    from apps.cotisations.models import ParametresCotisations
    from apps.evenements.services import convoquer, creer_evenement

    p = ParametresCotisations.courant()
    p.mois_depart = timezone.localdate().replace(day=1)
    p.save()
    ev = creer_evenement(
        nom="Pèlerinage de la Nativité 2026",
        debut=timezone.make_aware(datetime.datetime(2026, 12, 24, 8)),
        avec_autorisation=True,
        sessions=["Session Culte"],
        par=compte_technique,
    )
    convoquer(ev, [monde["m1"]], session=ev.sessions.get(), par=None)
    return monde


def test_bn_voit_les_trois_rubriques(situe, client_technique):
    base = f"/bureau/national/membres/{situe['m1'].matricule}/"
    html = _html(client_technique, base)
    assert "Profil" in html and "Cotisation mensuelle" in html
    assert "Participation aux événements" in html
    html = _html(client_technique, base + "?rubrique=cotisations")
    assert "En retard de 1 mois" in html and "Total versé" in html
    html = _html(client_technique, base + "?rubrique=evenements")
    assert "Pèlerinage de la Nativité 2026" in html and "Session Culte" in html


def test_fiche_bn_a_aussi_les_rubriques(situe, client_technique):
    base = f"/membres/bn/{situe['m1'].matricule}/"
    assert "Participation aux événements" in _html(client_technique, base)
    html = _html(client_technique, base + "?rubrique=evenements")
    assert "Pèlerinage de la Nativité 2026" in html


def test_bureau_paroisse_sans_rubrique_evenements(situe):
    c = Client()
    c.force_login(situe["sec_p1"].compte)
    base = f"/bureau/paroisse-{situe['P1'].pk}/membres/{situe['m1'].matricule}/"
    html = _html(c, base)
    assert "Cotisation mensuelle" in html and "Participation aux événements" not in html
    assert "En retard de 1 mois" in _html(c, base + "?rubrique=cotisations")
    html = _html(c, base + "?rubrique=evenements")  # ignoré : retour au profil
    assert "Participation aux événements" not in html and "Parcours" in html
    assert "Non pointé" not in html  # pas d'historique des événements pour un bureau


def test_profil_par_defaut(situe, client_technique):
    html = _html(client_technique, f"/bureau/national/membres/{situe['m1'].matricule}/")
    assert "Parcours" in html


def test_annee_affichee_et_boutons_d_annees(situe, client_technique):
    from apps.cotisations.models import ParametresCotisations

    annee = timezone.localdate().year
    base = f"/bureau/national/membres/{situe['m1'].matricule}/?rubrique=cotisations"
    html = _html(client_technique, base)
    assert f"Année {annee}" in html
    assert f"annee={annee}" in html and f"annee={annee - 1}" not in html
    # Départ des cotisations l'année précédente : un bouton par année.
    p = ParametresCotisations.courant()
    p.mois_depart = datetime.date(annee - 1, 11, 1)
    p.save()
    m1 = situe["m1"]
    m1.date_enregistrement = timezone.make_aware(datetime.datetime(annee - 2, 1, 1))
    m1.save(update_fields=["date_enregistrement"])
    html = _html(client_technique, base)
    assert f"annee={annee - 1}" in html and f"annee={annee}" in html
    html = _html(client_technique, base + f"&annee={annee - 1}")
    assert f"Année {annee - 1}" in html and f"Total versé en {annee - 1}" in html
    # Année hors de la période : on revient à l'année en cours.
    assert f"Année {annee}" in _html(client_technique, base + "&annee=1990")
    assert f"Année {annee}" in _html(client_technique, base + "&annee=abc")


def test_mes_cotisations_par_annee(situe):
    from apps.cotisations.models import ParametresCotisations

    annee = timezone.localdate().year
    p = ParametresCotisations.courant()
    p.mois_depart = datetime.date(annee - 1, 11, 1)
    p.save()
    m1 = situe["m1"]
    m1.date_enregistrement = timezone.make_aware(datetime.datetime(annee - 2, 1, 1))
    m1.save(update_fields=["date_enregistrement"])
    c = Client()
    c.force_login(m1.compte)
    html = _html(c, "/cotisations/moi/")
    assert f"Année {annee}" in html and f"annee={annee - 1}" in html
    html = _html(c, f"/cotisations/moi/?annee={annee - 1}")
    assert f"Année {annee - 1}" in html
