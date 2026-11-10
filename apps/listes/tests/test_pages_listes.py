import re

import pytest


def _url(monde, cle="P1", niveau="paroisse"):
    return f"/bureau/{niveau}-{monde[cle].pk}/listes/"


@pytest.fixture
def client_sec(client, monde):
    client.force_login(monde["sec_p1"].compte)
    return client


def test_acces(client, monde):
    assert client.get(_url(monde)).status_code == 302  # anonyme → connexion
    client.force_login(monde["sec_p1"].compte)
    assert client.get(_url(monde)).status_code == 200
    assert client.get(_url(monde, "P2")).status_code == 404
    for qui in ("m1", "tresorier"):
        client.force_login(monde[qui].compte)
        assert client.get(_url(monde)).status_code == 404


def test_statut_actif_par_defaut(client_sec, monde):
    m1 = monde["m1"]
    m1.statut = "decede"
    m1.save()
    html = client_sec.get(_url(monde)).content.decode()
    assert "Adjovi" not in html and "Secretaire" in html
    html = client_sec.get(_url(monde) + "?envoye=1").content.decode()
    assert "Adjovi" in html


def test_colonnes_choisies(client_sec, monde):
    r = client_sec.get(_url(monde) + "?envoye=1&colonnes=matricule&colonnes=telephone")
    entetes = re.findall(r"<th>(.*?)</th>", r.content.decode())
    assert entetes == ["Matricule", "Téléphone"]
    assert r.context["page"].paginator.count == 3


def test_jamais_cip_ni_npi(client_sec, monde):
    r = client_sec.get(_url(monde) + "?envoye=1&colonnes=npi")
    assert r.status_code == 200 and r.context["page"] is None
    html = client_sec.get(_url(monde)).content.decode()
    assert "NPI" not in html and "CIP" not in html


def test_onglets(client_sec, monde):
    html = client_sec.get(f"/bureau/paroisse-{monde['P1'].pk}/membres/").content.decode()
    assert _url(monde) in html and f"/bureau/paroisse-{monde['P1'].pk}/statistiques/" in html


def test_erreur_affichee(client_sec, monde):
    r = client_sec.get(_url(monde) + "?envoye=1&age=entre&age_x=40&age_y=18")
    html = r.content.decode()
    assert r.status_code == 200 and "supérieur ou égal" in html and "<table" not in html


def test_liens_export_gardent_les_filtres(client_sec, monde):
    html = client_sec.get(_url(monde) + "?envoye=1&sexe=M").content.decode()
    assert "listes/pdf/?envoye=1&amp;sexe=M" in html
    assert "listes/excel/?envoye=1&amp;sexe=M" in html
