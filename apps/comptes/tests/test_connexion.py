import pytest

from apps.comptes.models import Compte


@pytest.fixture
def compte(db):
    c = Compte.objects.create_user("2015-01AS-0157", "MotDePasse!2026")
    c.doit_changer_mot_de_passe = False
    c.save()
    return c


def test_accueil_exige_connexion(client, db):
    r = client.get("/")
    assert r.status_code == 302 and r.url.startswith("/connexion/")


def test_connexion_avec_espaces_et_minuscules(client, compte):
    r = client.post("/connexion/", {"username": " 2015-01as-0157 ", "password": "MotDePasse!2026"})
    assert r.status_code == 302 and r.url == "/"


def test_mauvais_mot_de_passe_message_francais(client, compte):
    r = client.post("/connexion/", {"username": "2015-01AS-0157", "password": "faux"})
    assert "Identifiant ou mot de passe incorrect." in r.content.decode()


def test_page_connexion_mobile_et_francais(client, db):
    html = client.get("/connexion/").content.decode()
    assert 'lang="fr"' in html and 'name="viewport"' in html


def test_accueil_salue_le_membre(client, compte):
    client.force_login(compte)
    assert "Bienvenue, 2015-01AS-0157" in client.get("/").content.decode()


def test_deconnexion_post(client, compte):
    client.force_login(compte)
    r = client.post("/deconnexion/")
    assert r.status_code == 302 and r.url == "/connexion/"
    assert client.get("/").status_code == 302
