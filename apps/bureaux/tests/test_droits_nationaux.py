"""Droits au Bureau National de Commandement (décisions du 19/11/2026).

- Installer / remplacer / pourvoir un bureau, « Fonctions et droits », sanctions,
  enregistrement des membres : Président et Secrétaire national seulement (en dur).
- Cotisations spéciales : Président, Secrétaire, Trésorier national et son adjoint.
- Reversements : le Trésorier national ; l'adjoint seulement si le poste est vacant.
- Les autres pouvoirs viennent de cases séparées (membres, événements, grades, journal)."""

import pytest
from django.test import Client

from apps.bureaux.models import Fonction


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


@pytest.fixture
def bnc(monde, nouveau_membre, donner_mandat):
    """Président, Secrétaire national, Trésorier national (case « membres » cochée) et adjoint."""
    Fonction.objects.filter(nom="Trésorier national").update(droit_gerer=True)
    r = {}
    for nom, fonction in [
        ("pres", "Président"),
        ("sn", "Secrétaire national"),
        ("tn", "Trésorier national"),
        ("tna", "Trésorier national adjoint"),
    ]:
        r[nom] = nouveau_membre(monde["P1"], nom.upper())
        donner_mandat(r[nom], fonction)
    return dict(monde, **r)


@pytest.mark.parametrize(
    "url",
    [
        "/bureau/bn/installer/",
        "/bureau/bn/fonctions/",
        "/bureau/bn/mandats-a-corriger/",
        "/membres/bn/enregistrer/",
        "/lots/",
    ],
)
def test_reserve_au_president_et_au_secretaire(bnc, url):
    assert _client(bnc["pres"]).get(url).status_code == 200
    assert _client(bnc["sn"]).get(url).status_code == 200
    # Le Trésorier national, même avec la case « membres » cochée, n'y a pas accès.
    assert _client(bnc["tn"]).get(url).status_code in (403, 404)


def test_sanction_reservee(bnc):
    url = f"/bureau/bn/sanctions/{bnc['m1'].matricule}/nouvelle/"
    assert _client(bnc["sn"]).get(url).status_code == 200
    assert _client(bnc["tn"]).get(url).status_code in (403, 404)


def test_cotisations_speciales_creees_par_les_quatre(bnc):
    for qui in ("pres", "sn", "tn", "tna"):
        assert _client(bnc[qui]).get("/tresorerie/bn/speciales/").status_code == 200
    assert _client(bnc["m1"]).get("/tresorerie/bn/speciales/").status_code in (403, 404)


def test_reversements_adjoint_seulement_par_interim(bnc, donner_mandat):
    from apps.bureaux.perimetre import est_tresorier_national

    assert est_tresorier_national(bnc["tn"].compte)
    assert not est_tresorier_national(bnc["tna"].compte)
    import datetime

    bnc["tn"].mandats.update(date_fin=datetime.date.today())  # poste vacant
    assert est_tresorier_national(bnc["tna"].compte)


def test_cases_separees(bnc):
    """Le Trésorier avec la seule case « membres » n'a ni événements, ni grades, ni journal."""
    tn = bnc["tn"].compte
    assert tn.has_perm("membres.gerer_membres")
    for perm in ("evenements.gerer", "grades.gerer", "journal.voir"):
        assert not tn.has_perm(perm)
    Fonction.objects.filter(nom="Trésorier national").update(droit_grades=True)
    tn = type(tn).objects.get(pk=tn.pk)
    assert tn.has_perm("grades.gerer") and not tn.has_perm("evenements.gerer")
    # Président : tout, par ses cases (cochées par défaut) et ses droits en dur.
    pres = bnc["pres"].compte
    for perm in ("evenements.gerer", "grades.gerer", "journal.voir", "bureaux.installer"):
        assert pres.has_perm(perm)


def test_pages_suivent_les_cases(bnc):
    tn = _client(bnc["tn"])
    assert tn.get("/evenements/").status_code == 403
    assert tn.get("/grades/bn/eligibles/").status_code == 403
    assert tn.get("/journal/").status_code == 403
    assert _client(bnc["pres"]).get("/journal/").status_code == 200


def test_page_fonctions_et_droits_cases_separees(bnc):
    from apps.journal.models import EntreeJournal

    c = _client(bnc["pres"])
    page = c.get("/bureau/bn/fonctions/").content.decode()
    tn = Fonction.objects.get(nom="Trésorier national")
    assert (
        'name="case" value="droit_grades"' in page and "Président et au Secrétaire national" in page
    )
    c.post("/bureau/bn/fonctions/", {"fonction": tn.pk, "case": "droit_grades", "valeur": "on"})
    tn.refresh_from_db()
    assert tn.droit_grades
    assert EntreeJournal.objects.filter(action="droits_modifies").exists()
    # Une case inconnue est refusée ; une case nationale sur une fonction locale aussi.
    local = Fonction.objects.get(nom="Trésorier paroissial")
    c.post("/bureau/bn/fonctions/", {"fonction": local.pk, "case": "droit_grades", "valeur": "on"})
    local.refresh_from_db()
    assert not local.droit_grades
