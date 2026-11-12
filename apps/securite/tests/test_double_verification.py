import time

import pytest
from django.core.management import call_command

from apps.journal.models import EntreeJournal
from apps.securite.models import DoubleVerification
from apps.securite.totp import code_totp


@pytest.fixture
def bn(client, compte_technique):
    client.force_login(compte_technique)
    return client


def _activer(client):
    client.get("/securite/activer/")
    secret = client.session["double_verification_secret"]
    r = client.post("/securite/activer/", {"code": code_totp(secret, time.time())})
    return secret, r


def test_toutes_les_pages_bloquees(bn, monde):
    for url in (
        "/",
        "/bureau/national/listes/",
        "/gestion/",
        f"/membres/bn/{monde['m1'].matricule}/fiche.pdf",
        "/journal/",
        "/notifications/",
    ):
        r = bn.get(url)
        assert r.status_code == 302 and r.url.startswith("/securite/activer/"), url


def test_activation(bn, compte_technique):
    page = bn.get("/securite/activer/").content.decode()
    assert "<svg" in page and "Clé" in page
    r = bn.post("/securite/activer/", {"code": "000000"})
    assert r.status_code == 200 and not DoubleVerification.objects.filter(active=True).exists()
    secret, r = _activer(bn)
    assert r.status_code == 302
    dv = DoubleVerification.objects.get(compte=compte_technique)
    assert dv.active and dv.secret == secret
    assert bn.get("/").status_code == 200
    assert EntreeJournal.objects.filter(action="double_verification").exists()


def test_activation_impossible_si_deja_active(client, compte_technique):
    client.force_login(compte_technique)
    secret, _ = _activer(client)
    client.logout()
    client.force_login(compte_technique)
    r = client.get("/securite/activer/")
    assert r.status_code == 302 and r.url.startswith("/securite/code/")


def test_code_correct_ouvre_la_session(client, compte_technique):
    client.force_login(compte_technique)
    secret, _ = _activer(client)
    client.logout()
    client.force_login(compte_technique)
    assert client.get("/").url.startswith("/securite/code/")
    dv = DoubleVerification.objects.get()
    dv.dernier_pas = None
    dv.save()
    r = client.post("/securite/code/", {"code": code_totp(secret, time.time())})
    assert r.status_code == 302 and client.get("/").status_code == 200


def test_code_rejoue_refuse(client, compte_technique):
    client.force_login(compte_technique)
    secret, _ = _activer(client)
    code = code_totp(secret, time.time())  # déjà utilisé pour l'activation
    client.logout()
    client.force_login(compte_technique)
    r = client.post("/securite/code/", {"code": code})
    assert r.status_code == 200 and "incorrect" in r.content.decode()
    assert client.get("/").status_code == 302


def test_cinq_echecs_deconnecte(client, compte_technique):
    client.force_login(compte_technique)
    _activer(client)
    client.logout()
    client.force_login(compte_technique)
    for _ in range(4):
        assert client.post("/securite/code/", {"code": "000000"}).status_code == 200
    r = client.post("/securite/code/", {"code": "000000"})
    assert r.status_code == 302 and r.url.startswith("/connexion/")
    assert "_auth_user_id" not in client.session
    assert EntreeJournal.objects.filter(action="double_verification").count() >= 6


def test_membre_simple_non_concerne(client, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get("/").status_code == 200


def test_mandat_national_concerne(client, monde, donner_mandat):
    donner_mandat(monde["m1"], "Secrétaire national")
    client.force_login(monde["m1"].compte)
    assert client.get("/").url.startswith("/securite/activer/")


def test_deconnexion_reste_possible(bn):
    r = bn.post("/deconnexion/")
    assert r.status_code == 302 and "_auth_user_id" not in bn.session


def test_commande_reinitialisation(client, compte_technique):
    client.force_login(compte_technique)
    _activer(client)
    call_command("reinitialiser_double_verification", "tech")
    assert not DoubleVerification.objects.get().active
    client.logout()
    client.force_login(compte_technique)
    assert client.get("/").url.startswith("/securite/activer/")


def test_permission_bn_manuelle_concernee(client, monde):
    from django.contrib.auth.models import Permission

    compte = monde["m1"].compte
    compte.user_permissions.add(Permission.objects.get(codename="gerer_membres"))
    client.force_login(compte)
    assert client.get("/journal/").url.startswith("/securite/activer/")


def test_blocage_persiste_apres_reconnexion(client, compte_technique):
    client.force_login(compte_technique)
    secret, _ = _activer(client)
    client.logout()
    client.force_login(compte_technique)
    for _ in range(5):
        client.post("/securite/code/", {"code": "000000"})
    client.force_login(compte_technique)  # nouvelle connexion avec le bon mot de passe
    dv = DoubleVerification.objects.get()
    dv.dernier_pas = None
    dv.save()
    r = client.post("/securite/code/", {"code": code_totp(secret, time.time())})
    assert r.status_code == 200 and "Trop d" in r.content.decode()
    assert client.get("/").status_code == 302


def test_activation_possible_avec_un_seul_telephone(bn):
    html = bn.get("/securite/activer/").content.decode()
    secret = bn.session["double_verification_secret"]
    assert 'href="otpauth://totp/' in html and f"secret={secret}" in html
    assert "Ajouter à mon application d" in html
    assert "Copier la clé" in html and f'data-cle="{secret}"' in html
    assert html.index("otpauth://") < html.index("<svg")  # le bouton passe avant le QR code
