from html import unescape

import pytest

from apps.mouvements.models import Mutation
from apps.mouvements.services import demander_mutation


@pytest.fixture
def sec_p4(monde, nouveau_membre, donner_mandat):
    sec = nouveau_membre(monde["P4"], "SecP4")
    donner_mandat(sec, "Secrétaire paroissial", monde["P4"])
    return sec


def _cle(monde, niveau, nom):
    return f"{niveau}-{monde[nom].pk}"


def test_onglet_demandes(client, monde):
    client.force_login(monde["sec_p1"].compte)
    cle = _cle(monde, "paroisse", "P1")
    html = client.get(f"/bureau/{cle}/membres/").content.decode()
    assert f"/bureau/{cle}/demandes/" in html
    assert client.get(f"/bureau/{cle}/demandes/").status_code == 200


def test_paroisse_demande_mutation_en_deux_temps(client, monde, sec_p4):
    client.force_login(sec_p4.compte)
    url = f"/bureau/{_cle(monde, 'paroisse', 'P4')}/mutations/nouvelle/"
    m1 = monde["m1"]
    r = client.post(url, {"matricule": m1.matricule})
    html = unescape(r.content.decode())
    assert r.status_code == 200 and "Camarade Test ADJOVI" in html and "P1" in html
    assert m1.telephone not in html and not Mutation.objects.exists()
    r = client.post(url, {"matricule": m1.matricule, "motif": "Déménagement", "confirmer": "1"})
    mut = Mutation.objects.get()
    assert mut.paroisse_arrivee == monde["P4"] and mut.motif == "Déménagement"
    assert r.status_code == 302 and r.url.endswith(f"/mutations/{mut.pk}/")
    assert "En attente d'avis" in unescape(client.get(r.url).content.decode())


def test_nouvelle_mutation_reservee(client, monde):
    client.force_login(monde["chef"].compte)
    assert (
        client.get(f"/bureau/{_cle(monde, 'circuit', 'Ekpe A')}/mutations/nouvelle/").status_code
        == 404
    )
    client.force_login(monde["m1"].compte)
    assert (
        client.get(f"/bureau/{_cle(monde, 'paroisse', 'P1')}/mutations/nouvelle/").status_code
        == 404
    )


def test_national_choisit_paroisse(client_technique, monde):
    r = client_technique.post(
        "/bureau/national/mutations/nouvelle/",
        {"matricule": monde["m1"].matricule, "paroisse_arrivee": monde["P3"].pk, "confirmer": "1"},
    )
    assert r.status_code == 302 and Mutation.objects.get().paroisse_arrivee == monde["P3"]


def test_matricule_inconnu(client, monde, sec_p4):
    client.force_login(sec_p4.compte)
    url = f"/bureau/{_cle(monde, 'paroisse', 'P4')}/mutations/nouvelle/"
    r = client.post(url, {"matricule": "2099-99AS-9999", "confirmer": "1"})
    assert "Aucun membre avec ce matricule." in r.content.decode()
    assert not Mutation.objects.exists()


def test_refus_affiche(client, monde, sec_p4):
    client.force_login(sec_p4.compte)
    url = f"/bureau/{_cle(monde, 'paroisse', 'P4')}/mutations/nouvelle/"
    r = client.post(url, {"matricule": monde["m4"].matricule, "confirmer": "1"})
    assert "déjà dans cette paroisse" in r.content.decode() and not Mutation.objects.exists()


@pytest.fixture
def mutation(monde, compte_technique):
    return demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)


def test_avis_circuit(client, monde, mutation):
    client.force_login(monde["chef"].compte)
    cle = _cle(monde, "circuit", "Ekpe A")
    page = client.get(f"/bureau/{cle}/mutations/{mutation.pk}/").content.decode()
    assert 'name="favorable"' in page
    r = client.post(
        f"/bureau/{cle}/mutations/{mutation.pk}/avis/",
        {"favorable": "0", "commentaire": "Membre utile ici"},
    )
    assert r.status_code == 302
    page = client.get(r.url).content.decode()
    assert "Défavorable" in page and "Membre utile ici" in page and 'name="favorable"' not in page


def test_avis_mauvais_circuit_404(client, monde, mutation, nouveau_membre, donner_mandat):
    chef_b = nouveau_membre(monde["P3"], "ChefB")
    donner_mandat(chef_b, "Chef de Section de Circuit", monde["Ekpe B"])
    client.force_login(chef_b.compte)
    cle = _cle(monde, "circuit", "Ekpe B")
    r = client.post(f"/bureau/{cle}/mutations/{mutation.pk}/avis/", {"favorable": "1"})
    assert r.status_code == 404 and not mutation.avis.exists()


def test_paroisse_ne_donne_pas_avis(client, monde, mutation):
    client.force_login(monde["sec_p1"].compte)
    cle = _cle(monde, "paroisse", "P1")
    assert (
        'name="favorable"'
        not in client.get(f"/bureau/{cle}/mutations/{mutation.pk}/").content.decode()
    )
    r = client.post(f"/bureau/{cle}/mutations/{mutation.pk}/avis/", {"favorable": "1"})
    assert r.status_code == 404


def test_mutation_hors_perimetre_404(client, monde, mutation, nouveau_membre, donner_mandat):
    sec_p3 = nouveau_membre(monde["P3"], "SecP3")
    donner_mandat(sec_p3, "Secrétaire paroissial", monde["P3"])
    client.force_login(sec_p3.compte)
    cle = _cle(monde, "paroisse", "P3")
    assert client.get(f"/bureau/{cle}/mutations/{mutation.pk}/").status_code == 404
    assert client.get(f"/bureau/mutations/{mutation.pk}/").status_code == 404


def test_aiguillage_notification(client, monde, mutation):
    client.force_login(monde["sec_p1"].compte)
    r = client.get(f"/bureau/mutations/{mutation.pk}/")
    assert r.status_code == 302
    assert r.url == f"/bureau/{_cle(monde, 'paroisse', 'P1')}/mutations/{mutation.pk}/"


def test_demandes_listent_la_mutation(client, monde, mutation, sec_p4):
    client.force_login(sec_p4.compte)
    html = unescape(
        client.get(f"/bureau/{_cle(monde, 'paroisse', 'P4')}/demandes/").content.decode()
    )
    assert monde["m1"].matricule in html and "En attente d'avis" in html
