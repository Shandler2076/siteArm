"""Page « Parts reçues » : paroisses classées par région et circuit, effectif, recherche."""

import datetime
from html import unescape

import pytest
from django.test import Client

from apps.cotisations.services import saisir_versement, valider
from apps.cotisations.tests.conftest import enregistre_le

D = datetime.date


@pytest.fixture
def prets(monde, depart):
    for k in ("m1", "sec_p1", "tresorier", "m2", "m3", "m4"):
        enregistre_le(monde[k], D(2025, 1, 1))
    v = saisir_versement(monde["m1"], montant=300, date_versement=D(2026, 3, 1), par=None)
    valider([v], par=None)
    return monde


def _html(client, url):
    return unescape(client.get(url).content.decode())


def test_parts_classees_region_circuit_paroisse_avec_effectif(prets, client_technique):
    html = _html(client_technique, "/cotisations/national/parts/")
    # Région, puis circuit, puis paroisse, dans cet ordre.
    i_region = html.index("03 — HOULENOU")
    i_circuit = html.index("Circuit de Ekpe A")
    i_paroisse = html.index("Paroisse P1")
    assert i_region < i_circuit < i_paroisse
    # P1 : Adjovi, Secretaire, Tresorier = 3 membres ; peut payer 3 × 100 F = 300 F par mois.
    assert "3 membres" in html and "300 F par mois" in html
    assert "05 — WEME" in html and "Paroisse P4" in html


def test_recherche_par_nom_de_paroisse(prets, client_technique):
    html = _html(client_technique, "/cotisations/national/parts/?q=p4")
    assert "Paroisse P4" in html and "Paroisse P1" not in html


def test_parts_du_circuit_limitees_a_ses_paroisses(prets):
    c = Client()
    c.force_login(prets["chef"].compte)
    html = _html(c, f"/cotisations/circuit-{prets['Ekpe A'].pk}/parts/")
    assert "Paroisse P1" in html and "Paroisse P2" in html
    assert "Paroisse P3" not in html and "Paroisse P4" not in html
