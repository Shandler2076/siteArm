from datetime import date
from html import unescape

import pytest

from apps.mouvements.models import Signalement
from apps.mouvements.services import demander_mutation, signaler
from apps.mouvements.statuts import changer_statut


@pytest.fixture
def mutation(monde, compte_technique):
    return demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)


@pytest.fixture
def deces(monde):
    return signaler(
        membre=monde["m2"],
        type="deces",
        par=monde["chef"].compte,
        unite="national",
        date_effet=date(2026, 11, 1),
    )


def test_decisions_reservees_au_bn(client, monde, mutation, deces):
    client.force_login(monde["sec_p1"].compte)
    for url in (
        "/bureau/bn/decisions/",
        f"/bureau/bn/mutations/{mutation.pk}/",
        f"/bureau/bn/signalements/{deces.pk}/",
    ):
        assert client.get(url).status_code == 403
        assert client.post(url, {"decision": "valider"}).status_code == 403
    mutation.refresh_from_db()
    assert mutation.etat == "avis"


def test_liste_decisions(client_technique, monde, mutation, deces):
    html = unescape(client_technique.get("/bureau/bn/decisions/").content.decode())
    assert f"/bureau/bn/mutations/{mutation.pk}/" in html
    assert f"/bureau/bn/signalements/{deces.pk}/" in html
    assert monde["m1"].matricule in html and "Décès" in html


def test_valider_mutation_page(client_technique, monde, mutation):
    page = unescape(client_technique.get(f"/bureau/bn/mutations/{mutation.pk}/").content.decode())
    assert "Avis du circuit de départ : pas encore donné" in page
    r = client_technique.post(f"/bureau/bn/mutations/{mutation.pk}/", {"decision": "valider"})
    assert r.status_code == 302
    assert monde["m1"].affectation_actuelle.paroisse == monde["P4"]
    assert "Mutation validée." in client_technique.get(r.url).content.decode()


def test_mutation_page_signale_mandats(client_technique, monde, compte_technique):
    mut = demander_mutation(
        membre=monde["sec_p1"], paroisse_arrivee=monde["P4"], par=compte_technique
    )
    page = unescape(client_technique.get(f"/bureau/bn/mutations/{mut.pk}/").content.decode())
    assert "Secrétaire paroissial" in page and "seront clos" in page


def test_refus_signalement_motif_obligatoire(client_technique, monde, deces):
    url = f"/bureau/bn/signalements/{deces.pk}/"
    r = client_technique.post(url, {"decision": "refuser", "motif_refus": ""})
    assert r.status_code == 200 and "motif" in r.content.decode()
    deces.refresh_from_db()
    assert deces.etat == "bn"
    r = client_technique.post(url, {"decision": "refuser", "motif_refus": "Erreur"})
    deces.refresh_from_db()
    assert r.status_code == 302 and deces.etat == "refusee"


def test_confirmer_deces_page(client_technique, monde, deces):
    r = client_technique.post(f"/bureau/bn/signalements/{deces.pk}/", {"decision": "valider"})
    monde["m2"].refresh_from_db()
    assert r.status_code == 302 and monde["m2"].statut == "decede"


def test_rehabilitation_renvoie_pdf(client_technique, monde, compte_technique):
    m1 = monde["m1"]
    changer_statut(m1, "demissionnaire", par=None, date_effet=date(2025, 1, 1), motif="Démission")
    sig = signaler(membre=m1, type="rehabilitation", par=compte_technique, unite="national")
    r = client_technique.post(f"/bureau/bn/signalements/{sig.pk}/", {"decision": "valider"})
    assert r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert f"fiche-{m1.matricule}.pdf" in r["Content-Disposition"]
    assert "no-store" in r["Cache-Control"]
    m1.refresh_from_db()
    assert m1.statut == "actif"


def test_decision_refusee_affiche_message(client_technique, monde, mutation):
    m1 = monde["m1"]
    m1.statut = "decede"
    m1.save()
    r = client_technique.post(f"/bureau/bn/mutations/{mutation.pk}/", {"decision": "valider"})
    assert r.status_code == 200 and "La situation du membre a changé" in unescape(
        r.content.decode()
    )
    assert m1.affectations.count() == 1


def test_deja_traitee(client_technique, monde, deces):
    url = f"/bureau/bn/signalements/{deces.pk}/"
    client_technique.post(url, {"decision": "valider"})
    r = client_technique.post(url, {"decision": "valider"})
    assert r.status_code == 200 and "déjà été traitée" in unescape(r.content.decode())
    assert Signalement.objects.get().etat == "validee"


def test_aiguillage_bn(client_technique, mutation):
    r = client_technique.get(f"/bureau/mutations/{mutation.pk}/")
    assert r.status_code == 302 and r.url == f"/bureau/bn/mutations/{mutation.pk}/"


def test_lien_accueil(client_technique, mutation):
    html = unescape(client_technique.get("/").content.decode())
    assert "/bureau/bn/decisions/" in html and "Décisions à prendre (1)" in html
