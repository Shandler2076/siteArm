"""Validité de l'autorisation limitée dans le temps (décision du BNC du 12/11/2026)."""

import datetime
import io
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone
from pypdf import PdfReader

from apps.evenements.services import autorisation_valable, convoquer, creer_evenement, etat_scan

DEBUT = timezone.make_aware(datetime.datetime(2026, 12, 24, 7, 0))


@pytest.fixture
def ev(db, compte_technique):
    return creer_evenement(
        nom="Pèlerinage de la Nativité 2026",
        debut=DEBUT,
        avec_autorisation=True,
        validite_debut=DEBUT - datetime.timedelta(hours=1),
        validite_heures=48,
        par=compte_technique,
    )


def test_fin_de_validite(ev):
    assert ev.debut_validite == DEBUT - datetime.timedelta(hours=1)
    assert ev.fin_validite == DEBUT + datetime.timedelta(hours=47)


def test_valide_par_defaut_24_heures_depuis_le_debut(db, compte_technique):
    ev = creer_evenement(nom="X", debut=DEBUT, avec_autorisation=True, par=compte_technique)
    assert ev.debut_validite == DEBUT and ev.fin_validite == DEBUT + datetime.timedelta(hours=24)


def test_etats_du_scan(monde, ev):
    (c,) = convoquer(ev, [monde["m1"]], par=None)
    avant = DEBUT - datetime.timedelta(hours=2)
    pendant = DEBUT + datetime.timedelta(hours=10)
    apres = DEBUT + datetime.timedelta(hours=48)
    assert etat_scan(c, avant)[0] == "pas_encore"
    assert etat_scan(c, pendant)[0] == "valable"
    assert etat_scan(c, apres)[0] == "expiree"
    assert autorisation_valable(c, avant) and autorisation_valable(c, pendant)
    assert not autorisation_valable(c, apres)


def test_page_de_verification_expiree(monde, ev, monkeypatch):
    import apps.evenements.views as v

    (c,) = convoquer(ev, [monde["m1"]], par=None)
    monkeypatch.setattr(v, "maintenant", lambda: DEBUT + datetime.timedelta(hours=60))
    html = unescape(Client().get(f"/evenements/verifier/{c.jeton}/").content.decode())
    assert "Non valable" in html and "expirée" in html
    monkeypatch.setattr(v, "maintenant", lambda: DEBUT - datetime.timedelta(hours=5))
    html = unescape(Client().get(f"/evenements/verifier/{c.jeton}/").content.decode())
    assert "Pas encore valable" in html and "24/12/2026 à 06:00" in html


def test_carte_porte_la_periode_de_validite(monde, ev):
    (c,) = convoquer(ev, [monde["m1"]], par=None)
    client = Client()
    client.force_login(monde["m1"].compte)
    contenu = client.get(f"/evenements/autorisation/{c.pk}.pdf").content
    texte = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages)
    assert "Valable du 24/12/2026 06:00 au 26/12/2026 06:00" in texte


def test_formulaire_duree(monde, client_technique):
    client_technique.post(
        "/evenements/nouveau/",
        {
            "nom": "Pèlerinage",
            "debut_date": "2026-12-24",
            "debut_heure": "07:00",
            "avec_autorisation": "on",
            "validite_date": "2026-12-24",
            "validite_heure": "05:00",
            "validite_heures": "12",
        },
    )
    from apps.evenements.models import Evenement

    ev = Evenement.objects.get()
    assert ev.validite_heures == 12
    assert timezone.localtime(ev.fin_validite).strftime("%d/%m %H:%M") == "24/12 17:00"
