import pytest

from apps.comptes.models import Compte


@pytest.fixture
def compte(db):
    c = Compte.objects.create_user("2015-01AS-0157", "MotDePasse!2026")
    c.doit_changer_mot_de_passe = False
    c.save()
    return c


def _essai(client, mdp, ident="2015-01AS-0157"):
    return client.post("/connexion/", {"username": ident, "password": mdp})


def test_bloque_apres_5_echecs_meme_avec_bon_mot_de_passe(client, compte):
    for _ in range(5):
        _essai(client, "faux")
    r = _essai(client, "MotDePasse!2026")
    assert r.status_code == 429
    assert "bloqué pendant 15 minutes" in r.content.decode()


def test_variantes_d_ecriture_comptent_ensemble(client, compte):
    for ident in [
        "2015-01as-0157",
        " 2015-01AS-0157",
        "2015-01AS-0157 ",
        "2015-01aS-0157",
        "2015-01As-0157",
    ]:
        _essai(client, "faux", ident)
    assert _essai(client, "MotDePasse!2026").status_code == 429


def test_4_echecs_puis_succes(client, compte):
    for _ in range(4):
        _essai(client, "faux")
    assert _essai(client, "MotDePasse!2026").status_code == 302


def test_blocage_d_un_compte_n_affecte_pas_les_autres(client, compte):
    autre = Compte.objects.create_user("2016-02AS-0001", "AutreMot!2026")
    autre.doit_changer_mot_de_passe = False
    autre.save()
    for _ in range(5):
        _essai(client, "faux")
    assert _essai(client, "AutreMot!2026", "2016-02AS-0001").status_code == 302


def test_reglages_session(settings):
    assert settings.SESSION_COOKIE_AGE == 7200
    assert settings.SESSION_SAVE_EVERY_REQUEST is True
    assert settings.SESSION_COOKIE_HTTPONLY is True
