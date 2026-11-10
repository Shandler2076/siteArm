import pytest

from apps.comptes.models import Compte

URL = "/mot-de-passe/changer/"


@pytest.fixture
def nouveau(client, db):
    c = Compte.objects.create_user("2015-01AS-0157", "Provisoire!2026")
    client.force_login(c)
    return c


def _changer(client, nouveau_mdp, ancien="Provisoire!2026"):
    return client.post(
        URL, {"old_password": ancien, "new_password1": nouveau_mdp, "new_password2": nouveau_mdp}
    )


@pytest.mark.parametrize("chemin", ["/", "/gestion/"])
def test_redirection_tant_que_non_change(client, nouveau, chemin):
    r = client.get(chemin)
    assert r.status_code == 302 and r.url == URL


def test_page_de_changement_accessible(client, nouveau):
    assert client.get(URL).status_code == 200


def test_deconnexion_reste_possible(client, nouveau):
    assert client.post("/deconnexion/").url == "/connexion/"


def test_refuse_identifiant_comme_mot_de_passe(client, nouveau):
    r = _changer(client, "2015-01as-0157")
    assert "ne doit pas être votre identifiant" in r.content.decode()


def test_refuse_trop_court(client, nouveau):
    r = _changer(client, "Ab1!")
    assert r.status_code == 200
    nouveau.refresh_from_db()
    assert nouveau.doit_changer_mot_de_passe is True


def test_refuse_mot_de_passe_courant(client, nouveau):
    assert _changer(client, "password123").status_code == 200


def test_changement_reussi_libere_le_compte(client, nouveau):
    r = _changer(client, "Nouveau!Salut2026")
    assert r.status_code == 302 and r.url == "/"
    nouveau.refresh_from_db()
    assert nouveau.doit_changer_mot_de_passe is False
    assert client.get("/").status_code == 200
