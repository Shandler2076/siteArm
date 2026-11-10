import io

import pytest
from pypdf import PdfReader

from apps.lots.controle import creer_lot
from apps.lots.generation import valider_lot


def _l(nom):
    return [
        nom,
        "Test",
        "M",
        "",
        "",
        "",
        "",
        "0197000000",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        2015,
        "P1",
        "",
    ]


@pytest.fixture
def lot_valide(territoire, compte_technique, classeur):
    lot = creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([_l("Agbo"), _l("Bio")]),
    )
    valider_lot(lot, compte_technique)
    lot.refresh_from_db()
    return lot


def _pages(contenu):
    return [p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages]


def test_fiches_du_lot_une_page_par_membre(client_technique, lot_valide):
    url = f"/lots/{lot_valide.pk}/fiches.pdf"
    assert client_technique.get(url).status_code == 405
    r = client_technique.post(url)
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    pages = _pages(r.content)
    membres = [x.membre for x in lot_valide.lignes.all()]
    assert len(pages) == len(membres) == 2
    for page, membre in zip(pages, membres, strict=True):
        membre.compte.refresh_from_db()
        assert membre.matricule in page and "première connexion" in page
        mots = [w for w in page.split() if len(w) == 10 and membre.compte.check_password(w)]
        assert len(mots) == 1
        assert membre.compte.doit_changer_mot_de_passe


def test_recapitulatif_sans_mot_de_passe(client_technique, lot_valide):
    r = client_technique.get(f"/lots/{lot_valide.pk}/recapitulatif.pdf")
    texte = " ".join(_pages(r.content))
    assert r.status_code == 200
    assert "2015-03AS-0001" in texte and "AGBO" in texte and f"Lot n° {lot_valide.pk}" in texte
    assert "Mot de passe" not in texte


def test_lot_brouillon_404(client_technique, territoire, compte_technique, classeur):
    lot = creer_lot(
        region=territoire["HOULENOU"], par=compte_technique, fichier=classeur([_l("Agbo")])
    )
    assert client_technique.post(f"/lots/{lot.pk}/fiches.pdf").status_code == 404
    assert client_technique.get(f"/lots/{lot.pk}/recapitulatif.pdf").status_code == 404


def test_reserve_au_bn(client, territoire, nouveau_membre, lot_valide):
    client.force_login(nouveau_membre(territoire["P2"], "X").compte)
    assert client.post(f"/lots/{lot_valide.pk}/fiches.pdf").status_code == 403


def test_boutons_sur_la_page_resultat(client_technique, lot_valide):
    html = client_technique.get(f"/lots/{lot_valide.pk}/resultat/").content.decode()
    assert "fiches.pdf" in html and "recapitulatif.pdf" in html
    assert "nouveaux mots de passe provisoires remplacent les anciens" in html
