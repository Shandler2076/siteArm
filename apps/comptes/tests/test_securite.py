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


def test_essais_en_rafale_depuis_une_meme_adresse_bloques(client, compte, settings):
    """Faille M2 : essayer un mot de passe sur beaucoup d'identifiants différents depuis la même
    adresse IP finit par bloquer cette adresse (seuil large : beaucoup de gens au Bénin partagent
    une même adresse IP chez leur opérateur mobile)."""
    from django.test import Client

    for i in range(settings.LIMITE_ECHECS_PAR_IP):
        _essai(client, "faux", f"2020-01AS-{i:04d}")
    assert _essai(client, "MotDePasse!2026").status_code == 429
    autre = Client(REMOTE_ADDR="10.9.9.9")
    assert _essai(autre, "MotDePasse!2026").status_code == 302


def test_adresse_ip_derriere_le_relais(rf, settings):
    from apps.comptes.securite import adresse_ip

    r = rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="6.6.6.6, 41.85.1.2")
    settings.DERRIERE_RELAIS = False
    assert adresse_ip(r) == "10.0.0.1"
    settings.DERRIERE_RELAIS = True
    # La dernière adresse est celle ajoutée par le relais ; la première peut être inventée.
    assert adresse_ip(r) == "41.85.1.2"


def test_connexion_de_la_gestion_renvoie_vers_la_connexion_du_site(client, db):
    """Relecture : /gestion/login/ contournait la limite par adresse IP."""
    r = client.post("/gestion/login/", {"username": "x", "password": "y"})
    assert r.status_code == 302 and r.url.startswith("/connexion/")


def test_adresse_relais_invalide_ignoree(rf, settings):
    from apps.comptes.securite import adresse_ip

    settings.DERRIERE_RELAIS = True
    r = rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, abc")
    assert adresse_ip(r) == "10.0.0.1"


def test_gestion_sans_boucle_pour_un_membre_connecte(client, compte):
    """Un membre connecté (pas compte technique) qui ouvre /gestion/ ne tourne pas en rond entre
    /gestion/login/ et /connexion/ : il reçoit un refus clair."""
    client.force_login(compte)
    r = client.get("/gestion/", follow=True)
    assert r.status_code == 403 and len(r.redirect_chain) <= 2
    assert "Accès refusé" in r.content.decode()
