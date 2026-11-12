import datetime
import io
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone

from apps.evenements.models import Convocation, Evenement, Presence
from apps.evenements.services import convoquer, creer_evenement
from apps.membres.models import Membre


def _html(r):
    return unescape(r.content.decode())


@pytest.fixture
def ev(db, compte_technique):
    return creer_evenement(
        nom="Pèlerinage de la Nativité 2026",
        debut=timezone.make_aware(datetime.datetime(2026, 12, 24, 8, 0)),
        lieu="Porto-Novo",
        avec_autorisation=True,
        sessions=["Session Mère", "Session Culte"],
        par=compte_technique,
    )


@pytest.mark.parametrize("qui", ["chef", "sec_p1", "m1"])
def test_pages_reservees_au_bn(monde, ev, qui):
    c = Client()
    c.force_login(monde[qui].compte)
    for url in (
        "/evenements/",
        "/evenements/nouveau/",
        f"/evenements/{ev.pk}/",
        f"/evenements/{ev.pk}/convoquer/",
        f"/evenements/{ev.pk}/pointage/",
    ):
        assert c.get(url).status_code == 403, url


def test_creer_un_evenement(monde, client_technique):
    r = client_technique.post(
        "/evenements/nouveau/",
        {
            "nom": "Conclave du Bureau national",
            "debut": "2026-12-01T09:00",
            "lieu": "Siège",
            "sessions": "",
        },
    )
    ev = Evenement.objects.get()
    assert r.status_code == 302 and r.url.endswith(f"/evenements/{ev.pk}/")
    assert not ev.avec_autorisation


def test_creer_puis_convoquer_par_filtres(monde, ev, client_technique):
    Membre.objects.filter(pk__in=[monde["m1"].pk, monde["m4"].pk]).update(grade=5)
    url = f"/evenements/{ev.pk}/convoquer/"
    html = _html(client_technique.get(url + f"?envoye=1&grade=5&region={monde['HOULENOU'].pk}"))
    assert "Test ADJOVI" in html and "Test DOSSOU" not in html
    culte = ev.sessions.get(nom="Session Culte")
    r = client_technique.post(url, {"membres": [monde["m1"].pk], "session": culte.pk})
    assert r.status_code == 302
    c = Convocation.objects.get()
    assert c.membre == monde["m1"] and c.session == culte


def test_detail_par_session_et_retrait(monde, ev, client_technique):
    culte = ev.sessions.get(nom="Session Culte")
    (c,) = convoquer(ev, [monde["m1"]], session=culte, par=None)
    html = _html(client_technique.get(f"/evenements/{ev.pk}/"))
    assert "Session Culte" in html and "Test ADJOVI" in html
    r = client_technique.post(
        f"/evenements/{ev.pk}/", {"action": "retirer", "convocation": c.pk, "motif": "Erreur"}
    )
    assert r.status_code == 302
    c.refresh_from_db()
    assert not c.active


def test_pointage(monde, ev, client_technique):
    (c,) = convoquer(ev, [monde["m1"]], par=None)
    url = f"/evenements/{ev.pk}/pointage/"
    assert "Test ADJOVI" in _html(client_technique.get(url + "?q=adjovi"))
    r = client_technique.post(url, {"convocation": c.pk, "presence": "present"})
    assert r.status_code == 302
    c.refresh_from_db()
    assert c.presence == Presence.PRESENT


def test_annuler_l_evenement(monde, ev, client_technique):
    r = client_technique.post(
        f"/evenements/{ev.pk}/", {"action": "annuler", "motif": "Intempéries"}
    )
    assert r.status_code == 302
    ev.refresh_from_db()
    assert ev.annule


def test_export_convoques_sans_npi(monde, ev, client_technique):
    from openpyxl import load_workbook

    Membre.objects.filter(pk=monde["m1"].pk).update(npi="1234567890")
    convoquer(ev, [monde["m1"]], session=ev.sessions.first(), par=None)
    r = client_technique.get(f"/evenements/{ev.pk}/convoques.xlsx")
    valeurs = [
        c.value for ligne in load_workbook(io.BytesIO(r.content)).active.iter_rows() for c in ligne
    ]
    assert "Test" in valeurs and "1234567890" not in [str(v) for v in valeurs]
    r = client_technique.get(f"/evenements/{ev.pk}/convoques.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
