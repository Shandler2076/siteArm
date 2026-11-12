"""Corrections de la relecture finale (module 3)."""

import datetime
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone

from apps.evenements.models import Convocation
from apps.evenements.services import (
    EvenementRefuse,
    autorisation_valable,
    convocation_par_jeton,
    convoquer,
    creer_evenement,
)
from apps.journal.models import EntreeJournal
from apps.membres.models import Membre


def _html(r):
    return unescape(r.content.decode())


@pytest.fixture
def ev(db, compte_technique):
    return creer_evenement(
        nom="Pèlerinage de la Nativité 2026",
        debut=timezone.make_aware(datetime.datetime(2026, 12, 24, 8, 0)),
        avec_autorisation=True,
        sessions=["Session Mère", "Session Culte"],
        par=compte_technique,
    )


@pytest.mark.parametrize("statut", ["decede", "exclu", "demissionnaire"])
def test_carte_non_valable_apres_sortie(monde, ev, statut):
    (c,) = convoquer(ev, [monde["m1"]], par=None)
    Membre.objects.filter(pk=monde["m1"].pk).update(statut=statut)
    c = Convocation.objects.get(pk=c.pk)
    assert not autorisation_valable(c)
    assert "Non valable" in _html(Client().get(f"/evenements/verifier/{c.jeton}/"))


def test_convoquer_refuse_un_membre_sorti(monde, ev):
    Membre.objects.filter(pk=monde["m2"].pk).update(statut="exclu")
    m2 = Membre.objects.get(pk=monde["m2"].pk)
    with pytest.raises(EvenementRefuse, match="Test BIO"):
        convoquer(ev, [monde["m1"], m2], par=None)
    assert not Convocation.objects.exists()


def test_jetons_mal_formes(db):
    for jeton in ("\x00", "a b", "x'--", "é", "a" * 65):
        assert convocation_par_jeton(jeton) is None
    assert Client().get("/evenements/verifier/%00/").status_code in (200, 404)


def test_changement_de_session_journalise(monde, ev):
    mere, culte = ev.sessions.all()
    convoquer(ev, [monde["m1"]], session=mere, par=None)
    avant = EntreeJournal.objects.count()
    convoquer(ev, [monde["m1"]], session=culte, par=None)
    assert EntreeJournal.objects.count() == avant + 1


def test_retour_sans_session(monde, ev):
    mere = ev.sessions.first()
    (c,) = convoquer(ev, [monde["m1"]], session=mere, par=None)
    convoquer(ev, [monde["m1"]], session=None, par=None, sans_session=True)
    c.refresh_from_db()
    assert c.session is None


def test_lien_de_pointage_apres_scan_pour_le_bn(monde, ev, client_technique):
    (c,) = convoquer(ev, [monde["m1"]], par=None)
    html = _html(client_technique.get(f"/evenements/verifier/{c.jeton}/"))
    assert f"/evenements/{ev.pk}/pointage/?q={monde['m1'].matricule}" in html
    assert "pointage" not in _html(Client().get(f"/evenements/verifier/{c.jeton}/"))


def test_post_non_numerique_sans_erreur_500(monde, ev, client_technique):
    r = client_technique.post(f"/evenements/{ev.pk}/", {"action": "retirer", "convocation": "abc"})
    assert r.status_code == 404
    r = client_technique.post(f"/evenements/{ev.pk}/pointage/", {"convocation": "abc"})
    assert r.status_code == 404


def test_raison_evenement_sans_autorisation(monde, compte_technique):
    sans = creer_evenement(nom="Conclave", debut=timezone.now(), par=compte_technique)
    (c,) = convoquer(sans, [monde["m1"]], par=None)
    assert "ne donne pas lieu à une autorisation" in _html(
        Client().get(f"/evenements/verifier/{c.jeton}/")
    )


def test_photo_absente_sans_erreur(monde, ev, settings, tmp_path):
    from apps.membres.models import EtatPhoto, PhotoIdentite

    settings.PRIVATE_MEDIA_ROOT = str(tmp_path)
    PhotoIdentite.objects.create(
        membre=monde["m1"], fichier="prive/inexistante.jpg", etat=EtatPhoto.ACCEPTEE
    )
    (c,) = convoquer(ev, [monde["m1"]], par=None)
    assert Client().get(f"/evenements/verifier/{c.jeton}/").status_code == 200
    c2 = Client()
    c2.force_login(monde["m1"].compte)
    assert c2.get(f"/evenements/autorisation/{c.pk}.pdf").status_code == 200


def test_taux_de_presence(monde, ev, client_technique):
    from apps.evenements.models import Presence
    from apps.evenements.services import pointer

    c1, c2 = convoquer(ev, [monde["m1"], monde["m2"]], par=None)
    pointer(c1, Presence.PRESENT, par=None)
    pointer(c2, Presence.ABSENT, par=None)
    assert "50 %" in _html(client_technique.get(f"/evenements/{ev.pk}/"))
