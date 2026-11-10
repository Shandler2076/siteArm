import datetime

import pytest
from django.utils import timezone


@pytest.fixture
def secretaire_national(territoire, nouveau_membre, donner_mandat):
    m = nouveau_membre(territoire["P1"], "Natio")
    donner_mandat(m, "Secrétaire national", None, debut=datetime.date(2025, 1, 1))
    return m


def test_mandat_national_donne_les_pages_bnc(client, secretaire_national):
    client.force_login(secretaire_national.compte)
    assert client.get("/membres/bn/enregistrer/").status_code == 200
    assert secretaire_national.compte.has_perm("membres.voir_cip")


def test_mandat_de_paroisse_ne_donne_pas_les_pages_bnc(
    client, territoire, nouveau_membre, donner_mandat
):
    m = nouveau_membre(territoire["P1"], "Sec")
    donner_mandat(m, "Secrétaire paroissial", territoire["P1"], debut=datetime.date(2025, 1, 1))
    client.force_login(m.compte)
    assert client.get("/membres/bn/enregistrer/").status_code == 403


def test_fin_du_mandat_national_retire_les_droits(client, secretaire_national):
    mandat = secretaire_national.mandats.get()
    mandat.date_fin = timezone.localdate()
    mandat.save()
    client.force_login(secretaire_national.compte)
    assert client.get("/membres/bn/enregistrer/").status_code == 403


def test_compte_desactive_sans_droits(secretaire_national):
    c = secretaire_national.compte
    c.is_active = False
    c.save()
    assert not c.has_perm("membres.gerer_membres")


def test_session_bureau_30_minutes(client, secretaire_national):
    client.force_login(secretaire_national.compte)
    client.get("/")
    assert client.session.get_expiry_age() == 1800


def test_session_membre_2_heures(client, territoire, nouveau_membre):
    client.force_login(nouveau_membre(territoire["P1"], "Simple").compte)
    client.get("/")
    assert client.session.get_expiry_age() == 7200
