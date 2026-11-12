import datetime
from html import unescape

import pytest
from django.test import Client

from apps.cotisations.models import EtatVersement, Versement
from apps.cotisations.services import saisir_versement, valider
from apps.cotisations.tests.conftest import enregistre_le

D = datetime.date


@pytest.fixture(autouse=True)
def date_fixe(monkeypatch):
    import apps.cotisations.services as s
    import apps.cotisations.views as v

    monkeypatch.setattr(s, "aujourdhui", lambda: D(2026, 3, 15))
    monkeypatch.setattr(v, "aujourdhui", lambda: D(2026, 3, 15))


@pytest.fixture
def prets(monde, depart):
    for k in ("m1", "sec_p1", "tresorier", "m2", "m3"):
        enregistre_le(monde[k], D(2025, 1, 1))
    return monde


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _html(r):
    return unescape(r.content.decode())


def _p1(monde):
    return f"/cotisations/paroisse-{monde['P1'].pk}/"


def _circuit(monde):
    return f"/cotisations/circuit-{monde['Ekpe A'].pk}/"


def test_grille_paroisse(prets):
    r = _client(prets["sec_p1"]).get(_p1(prets) + "grille/")
    html = _html(r)
    assert r.status_code == 200 and "Test ADJOVI" in html and "Mar</th>" in html
    assert "Test BIO" not in html  # autre paroisse


def test_collecte_depuis_la_grille(prets):
    m1 = prets["m1"]
    r = _client(prets["tresorier"]).post(
        _p1(prets) + "grille/",
        {"date_versement": "2026-03-15", f"c-{m1.pk}": ["2026-01-01", "2026-02-01"]},
    )
    assert r.status_code == 302
    v = Versement.objects.get()
    assert v.montant == 200 and v.etat == EtatVersement.EN_ATTENTE


def test_versement_individuel(prets):
    m1 = prets["m1"]
    r = _client(prets["sec_p1"]).post(
        _p1(prets) + "versement/",
        {"membre": m1.pk, "montant": "300", "date_versement": "2026-03-15"},
    )
    assert r.status_code == 302 and Versement.objects.get().montant == 300
    r = _client(prets["sec_p1"]).post(
        _p1(prets) + "versement/",
        {"membre": m1.pk, "montant": "150", "date_versement": "2026-03-15"},
    )
    assert r.status_code == 200 and "nombre entier de mois" in _html(r)


def test_validation_par_le_circuit(prets):
    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    c = _client(prets["chef"])
    assert "Test ADJOVI" in _html(c.get(_circuit(prets) + "a-valider/"))
    r = c.post(_circuit(prets) + "a-valider/", {"action": "valider", "versements": [v.pk]})
    assert r.status_code == 302
    v.refresh_from_db()
    assert v.etat == EtatVersement.VALIDE


def test_refus_motif_obligatoire(prets):
    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    c = _client(prets["chef"])
    r = c.post(
        _circuit(prets) + "a-valider/", {"action": "refuser", "versements": [v.pk], "motif": ""}
    )
    assert r.status_code == 200 and "motif" in _html(r)
    c.post(
        _circuit(prets) + "a-valider/",
        {"action": "refuser", "versements": [v.pk], "motif": "Non reçu"},
    )
    v.refresh_from_db()
    assert v.etat == EtatVersement.REFUSE


def test_parts_du_circuit(prets):
    v = saisir_versement(prets["m1"], montant=300, date_versement=D(2026, 3, 1), par=None)
    (v,) = valider([v], par=None)
    c = _client(prets["chef"])
    html = _html(c.get(_circuit(prets) + "parts/"))
    assert "P1" in html and "60" in html
    mois = v.date_validation.date().replace(day=1).isoformat()
    r = c.post(_circuit(prets) + "parts/", {"paroisse": prets["P1"].pk, "mois": mois})
    assert r.status_code == 302 and "Reçue" in _html(c.get(_circuit(prets) + "parts/"))


def test_annulation_par_la_paroisse(prets):
    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    c = _client(prets["sec_p1"])
    r = c.post(f"/cotisations/versement/{v.pk}/annuler/", {"motif": "Erreur"})
    assert r.status_code == 302
    v.refresh_from_db()
    assert v.etat == EtatVersement.ANNULE


def test_paroisse_ne_peut_pas_annuler_un_versement_valide(prets):
    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    valider([v], par=None)
    r = _client(prets["sec_p1"]).post(f"/cotisations/versement/{v.pk}/annuler/", {"motif": "X"})
    assert r.status_code == 404


def test_tresorier_paroissial_saisit_mais_ne_voit_pas_les_fiches(prets):
    c = _client(prets["tresorier"])
    assert c.get(_p1(prets) + "grille/").status_code == 200
    cle = f"paroisse-{prets['P1'].pk}"
    assert c.get(f"/bureau/{cle}/membres/{prets['m1'].matricule}/").status_code == 404


def test_paroisse_ne_valide_pas(prets):
    cle = f"paroisse-{prets['P1'].pk}"
    assert _client(prets["sec_p1"]).get(f"/cotisations/{cle}/a-valider/").status_code == 404


def test_autre_paroisse_404(prets):
    assert (
        _client(prets["sec_p1"]).get(f"/cotisations/paroisse-{prets['P2'].pk}/grille/").status_code
        == 404
    )


def test_membre_simple_404(prets):
    assert _client(prets["m1"]).get(_p1(prets) + "grille/").status_code == 404


def test_menu_cotisations_pour_le_tresorier(prets):
    html = _html(_client(prets["tresorier"]).get("/"))
    assert "Cotisations mensuelles" in html and _p1(prets) in html
    assert "Cotisations mensuelles" not in _html(_client(prets["m1"]).get("/"))
