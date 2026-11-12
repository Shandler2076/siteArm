import datetime
import io
from html import unescape

import pytest
from django.test import Client
from pypdf import PdfReader

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
def donnees(monde, depart):
    for k in ("m1", "sec_p1", "tresorier"):
        enregistre_le(monde[k], D(2025, 1, 1))
    v = saisir_versement(monde["m1"], montant=300, date_versement=D(2026, 3, 1), par=None)
    (v,) = valider([v], par=None)  # m1 à jour (janvier à mars)
    saisir_versement(monde["sec_p1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    return dict(monde, recu=v)


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _texte_pdf(contenu):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages)


def test_tableau_de_bord_chiffres(donnees):
    html = unescape(
        _client(donnees["sec_p1"])
        .get(f"/cotisations/paroisse-{donnees['P1'].pk}/")
        .content.decode()
    )
    # P1 : m1 à jour ; sec_p1 (100 F en attente) et tresorier en retard de 3 mois.
    assert "À jour : 1" in html and "En retard : 2" in html
    assert "Validé : 300 F" in html and "En attente : 100 F" in html
    assert "Reste dû : 600 F" in html


def test_mes_cotisations_seulement_les_miennes(donnees):
    c = _client(donnees["m1"])
    html = unescape(c.get("/cotisations/moi/").content.decode())
    assert "À jour" in html and donnees["recu"].numero_recu in html
    assert "Test SECRETAIRE" not in html


def test_etat_pdf_contient_total_et_mention(donnees):
    texte = _texte_pdf(_client(donnees["m1"]).get("/cotisations/moi/etat.pdf").content)
    assert "ÉTAT DES COTISATIONS MENSUELLES" in texte.upper() and "300 F CFA" in texte
    assert "À jour au mars 2026" in texte
    texte = _texte_pdf(_client(donnees["tresorier"]).get("/cotisations/moi/etat.pdf").content)
    assert "En retard de 3 mois (300 F CFA)" in texte


def test_etat_pdf_d_un_membre_par_son_bureau(donnees):
    url = f"/cotisations/membre/{donnees['m1'].matricule}/etat.pdf"
    assert _client(donnees["tresorier"]).get(url).status_code == 200
    assert _client(donnees["sec_p1"]).get(url).status_code == 200
    assert _client(donnees["m2"]).get(url).status_code == 404  # membre simple d'une autre paroisse


def test_recu_pdf_apres_validation_seulement(donnees):
    v = donnees["recu"]
    texte = _texte_pdf(_client(donnees["m1"]).get(f"/cotisations/recu/{v.pk}.pdf").content)
    assert v.numero_recu in texte and "300 F" in texte and "janvier à mars 2026" in texte
    attente = donnees["sec_p1"].versements.get()
    assert _client(donnees["sec_p1"]).get(f"/cotisations/recu/{attente.pk}.pdf").status_code == 404
    assert _client(donnees["m2"]).get(f"/cotisations/recu/{v.pk}.pdf").status_code == 404


def test_fiche_pdf_sans_cotisations(donnees):
    from apps.membres.pdf import fiche_identification_pdf

    texte = _texte_pdf(fiche_identification_pdf(donnees["m1"]))
    assert "otisation" not in texte
