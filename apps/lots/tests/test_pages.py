import pytest

from apps.lots.colonnes import COLONNES
from apps.lots.controle import creer_lot
from apps.lots.models import EtatLigne, EtatLot


def _l(nom="Hounkpe", tel="0197000000", prenoms="Jean"):
    return [
        nom,
        prenoms,
        "M",
        "01/05/1990",
        "",
        "",
        "",
        tel,
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
def lot(territoire, compte_technique, classeur):
    return creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([_l(), _l(nom="Bio", tel="abc"), _l(nom="Chabi")]),
    )


def test_pages_reservees_au_bn(client, territoire, nouveau_membre, lot):
    client.force_login(nouveau_membre(territoire["P1"], "X").compte)
    for url in [
        "/lots/",
        "/lots/nouveau/",
        f"/lots/{lot.pk}/",
        f"/lots/{lot.pk}/lignes/2/",
        f"/lots/{lot.pk}/confirmer/",
    ]:
        assert client.get(url).status_code == 403, url


def test_liste(client_technique, lot):
    html = client_technique.get("/lots/").content.decode()
    assert f"Lot n° {lot.pk}" in html and "/lots/modele/03.xlsx" in html


def test_depot_puis_controle(client_technique, territoire, classeur):
    r = client_technique.post(
        "/lots/nouveau/",
        {
            "region": territoire["HOULENOU"].pk,
            "fichier": classeur([_l(), _l(nom="Bio", tel="abc"), _l(nom="Chabi")]),
        },
    )
    assert r.status_code == 302
    html = client_technique.get(r.url).content.decode()
    assert "3 lignes" in html and "Téléphone* : Numéro de téléphone invalide" in html
    assert "BIO" in html.upper()


def test_depot_fichier_invalide_message(client_technique, territoire, classeur):
    from apps.lots.models import Lot

    r = client_technique.post(
        "/lots/nouveau/",
        {
            "region": territoire["HOULENOU"].pk,
            "fichier": classeur([_l()], entetes_modifiees={0: "Nom"}),
        },
    )
    assert r.status_code == 200 and "modèle officiel" in r.content.decode()
    assert not Lot.objects.exists()


def test_bouton_valider_desactive_si_erreur(client_technique, lot):
    html = client_technique.get(f"/lots/{lot.pk}/").content.decode()
    assert 'id="valider" disabled' in html


def test_corriger_une_ligne(client_technique, lot, compte_technique):
    ligne = lot.lignes.get(numero=3)
    assert ligne.etat == EtatLigne.ERREUR
    data = dict(ligne.brutes)
    data["Téléphone*"] = "0161000000"
    # Ordre des colonnes du modèle (jsonb ne garde pas l'ordre des clés sous PostgreSQL)
    envoi = {
        f"c{i}": "" if data.get(c.entete) is None else data[c.entete]
        for i, c in enumerate(COLONNES)
    }
    r = client_technique.post(f"/lots/{lot.pk}/lignes/3/", envoi)
    assert r.status_code == 302
    ligne.refresh_from_db()
    assert ligne.etat == EtatLigne.CORRECTE and ligne.corrigee_par == compte_technique
    assert 'id="valider" disabled' not in client_technique.get(f"/lots/{lot.pk}/").content.decode()


def test_ecarter_puis_reprendre(client_technique, lot):
    client_technique.post(f"/lots/{lot.pk}/lignes/3/ecarter/")
    assert lot.lignes.get(numero=3).etat == EtatLigne.ECARTEE
    lot.refresh_from_db()
    assert lot.validable
    client_technique.post(f"/lots/{lot.pk}/lignes/3/reprendre/")
    assert lot.lignes.get(numero=3).etat == EtatLigne.ERREUR


def test_get_sur_action_405(client_technique, lot):
    assert client_technique.get(f"/lots/{lot.pk}/lignes/3/ecarter/").status_code == 405


def test_garder_un_doublon(client_technique, territoire, compte_technique, classeur):
    lot = creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([_l(), _l(nom="HOUNKPÈ")]),
    )
    assert {x.etat for x in lot.lignes.all()} == {EtatLigne.DOUBLON}
    client_technique.post(f"/lots/{lot.pk}/lignes/2/garder/")
    client_technique.post(f"/lots/{lot.pk}/lignes/3/ecarter/")
    lot.refresh_from_db()
    assert lot.lignes.get(numero=2).etat == EtatLigne.GARDEE and lot.validable


def test_garder_refuse_hors_doublon(client_technique, lot):
    r = client_technique.post(f"/lots/{lot.pk}/lignes/2/garder/")
    assert r.status_code == 400


def test_lot_valide_en_lecture_seule(client_technique, lot):
    lot.etat = EtatLot.VALIDE
    lot.save()
    assert client_technique.post(f"/lots/{lot.pk}/lignes/3/ecarter/").status_code == 403
    assert client_technique.post(f"/lots/{lot.pk}/lignes/3/", {}).status_code == 403


def test_redeposer(client_technique, lot, classeur):
    r = client_technique.post(f"/lots/{lot.pk}/", {"fichier": classeur([_l(nom="Dossou")])})
    assert r.status_code == 302
    assert [x.brutes["Nom*"] for x in lot.lignes.all()] == ["Dossou"]
