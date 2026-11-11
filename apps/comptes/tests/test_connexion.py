import pytest

from apps.comptes.models import Compte


@pytest.fixture
def compte(db):
    c = Compte.objects.create_user("2015-01AS-0157", "MotDePasse!2026")
    c.doit_changer_mot_de_passe = False
    c.save()
    return c


def test_page_d_accueil_publique(client, db):
    from html import unescape

    r = client.get("/")
    html = unescape(r.content.decode())
    assert r.status_code == 200
    assert 'href="/connexion/"' in html and "Se connecter" in html
    assert "FOI – AMOUR – JUSTICE" in html and "Armée du Salut du Bénin" in html
    assert "logo-congregation" in html and "logo-armee-du-salut" in html
    logos = html[html.index('class="vitrine-logos"') :]
    assert logos.index("logo-congregation") < logos.index("logo-armee-du-salut")  # Église à gauche
    assert 'class="menu"' not in html and "Bienvenue," not in html


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
    assert r.status_code == 302 and r.url == "/"
    assert "Se connecter" in client.get("/").content.decode()


def test_filigrane_sur_toutes_les_pages(client, compte):
    assert 'class="filigrane"' in client.get("/connexion/").content.decode()
    client.force_login(compte)
    assert 'class="filigrane"' in client.get("/").content.decode()


def test_connexion_propose_le_retour_a_l_accueil(client, db):
    assert 'href="/"' in client.get("/connexion/").content.decode()
