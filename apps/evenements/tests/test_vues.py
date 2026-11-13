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
            "debut_date": "2026-12-01",
            "debut_heure": "09:00",
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


# --- Décisions du 13/11/2026 : formulaire, sections, rôles, recherche ---------------------------


def test_date_passee_signalee_puis_confirmee(monde, client_technique):
    donnees = {"nom": "Conclave tenu", "debut_date": "2020-05-01", "debut_heure": "09:00"}
    r = client_technique.post("/evenements/nouveau/", donnees)
    assert r.status_code == 200 and "Revérifiez votre date" in _html(r)
    assert not Evenement.objects.exists()
    r = client_technique.post("/evenements/nouveau/", {**donnees, "confirmer_date_passee": "on"})
    assert r.status_code == 302 and Evenement.objects.count() == 1


def test_sections_seulement_si_option_choisie(monde, client_technique):
    base = {"nom": "Pèlerinage", "debut_date": "2026-12-24", "debut_heure": "07:00"}
    client_technique.post("/evenements/nouveau/", {**base, "sessions": "Section Mer"})
    sans = Evenement.objects.get()
    assert not sans.avec_sections and not sans.sessions.exists()
    client_technique.post(
        "/evenements/nouveau/",
        {
            **base,
            "nom": "Pèlerinage 2",
            "avec_sections": "on",
            "sessions": "Section Mer\nSection Culte",
        },
    )
    avec = Evenement.objects.get(nom="Pèlerinage 2")
    assert avec.avec_sections and [s.nom for s in avec.sessions.all()] == [
        "Section Mer",
        "Section Culte",
    ]
    html = _html(client_technique.get("/evenements/nouveau/"))
    assert "Sections (une par ligne)" in html and "Session Mère" not in html


def test_formulaire_heure_separee(monde, client_technique):
    html = _html(client_technique.get("/evenements/nouveau/"))
    assert 'name="debut_date"' in html and 'type="date"' in html
    assert 'name="debut_heure"' in html and 'type="time"' in html
    assert "Générer une autorisation pour les convoqués" in html and "option-bouton" in html


def test_recherche_membre_par_matricule_ou_nom(monde, ev, client_technique):
    url = f"/evenements/{ev.pk}/recherche-membres/"
    r = client_technique.get(url, {"q": monde["m1"].matricule}).json()
    assert [m["matricule"] for m in r["resultats"]] == [monde["m1"].matricule]
    r = client_technique.get(url, {"q": "dossou"}).json()
    assert [m["matricule"] for m in r["resultats"]] == [monde["m4"].matricule]
    assert client_technique.get(url, {"q": "a"}).json()["resultats"] == []


def test_recherche_reservee_au_bn(monde, ev):
    from django.test import Client

    c = Client()
    c.force_login(monde["sec_p1"].compte)
    assert c.get(f"/evenements/{ev.pk}/recherche-membres/", {"q": "adjovi"}).status_code == 403


def test_convoquer_superviseur_et_bureau(monde, ev, client_technique, donner_mandat):
    from apps.evenements.models import Role

    culte = ev.sessions.get(nom="Session Culte")
    url = f"/evenements/{ev.pk}/convoquer/"
    client_technique.post(
        url, {"membres": [monde["m1"].pk], "session": culte.pk, "role": "superviseur"}
    )
    c = Convocation.objects.get(membre=monde["m1"])
    assert c.role == Role.SUPERVISEUR and c.session == culte
    assert c.texte_formule == "Est autorisé(e) à participer"
    assert c.texte_role == "Invité(e) en tant que superviseur — Session Culte"
    # Bureau : jamais de section, le bureau représenté vient de ses mandats.
    client_technique.post(
        url, {"membres": [monde["sec_p1"].pk], "session": culte.pk, "role": "bureau"}
    )
    b = Convocation.objects.get(membre=monde["sec_p1"])
    assert b.role == Role.BUREAU and b.session is None and "P1" in b.bureau_libelle
    # Formule choisie : elle l'emporte sur celle du rôle.
    client_technique.post(
        url, {"membres": [monde["m2"].pk], "role": "superviseur", "formule": "travailler"}
    )
    assert Convocation.objects.get(membre=monde["m2"]).texte_formule == (
        "Est autorisé(e) à travailler"
    )


def test_page_convoquer_filtres_ranges_et_cascade(monde, ev, client_technique):
    html = _html(client_technique.get(f"/evenements/{ev.pk}/convoquer/"))
    assert "Rechercher un membre (matricule ou nom)" in html
    assert "Plus de filtres" in html and 'class="deroulant"' in html
    p1 = monde["P1"]
    assert f'data-circuit="{p1.circuit_id}"' in html
    assert f'data-region="{p1.circuit.region_id}"' in html
