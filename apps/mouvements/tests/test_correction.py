from datetime import date

import pytest
from django.contrib.auth import authenticate
from django.test import RequestFactory

from apps.journal.models import EntreeJournal
from apps.membres.services import CorrectionRefusee, corriger_integration
from apps.mouvements.services import decider_mutation, demander_mutation


def test_correction_paroisse_meme_region_garde_matricule(monde, compte_technique):
    m1 = monde["m1"]
    ancien = m1.matricule
    corriger_integration(
        membre=m1, annee=2015, paroisse=monde["P3"], motif="Erreur de saisie", par=compte_technique
    )
    m1.refresh_from_db()
    assert m1.matricule == ancien and m1.paroisse_integration == monde["P3"]
    a = m1.affectations.get()
    assert (a.paroisse, a.circuit_a_date) == (monde["P3"], monde["Ekpe B"])
    e = EntreeJournal.objects.get(action="correction_integration")
    assert e.details["avant"]["paroisse"] == "P1" and e.details["apres"]["paroisse"] == "P3"


def test_correction_region_nouveau_matricule(monde, compte_technique):
    m1 = monde["m1"]
    ancien = m1.matricule
    corriger_integration(
        membre=m1, annee=2016, paroisse=monde["P4"], motif="Reçu mal lu", par=compte_technique
    )
    m1.refresh_from_db()
    m1.compte.refresh_from_db()
    assert m1.matricule.startswith("2016-05AS-") and m1.matricule != ancien
    assert m1.compte.identifiant == m1.matricule
    assert m1.region_integration == monde["WEME"] and m1.annee_integration == 2016
    h = m1.historique.get(type="matricule")
    assert (h.ancien, h.nouveau) == (ancien, m1.matricule)
    assert h.libelle == f"Matricule : {ancien} → {m1.matricule}"
    assert m1.affectations.get().date_debut == date(2016, 1, 1)


def test_connexion_avec_nouveau_matricule(monde, compte_technique):
    m1 = monde["m1"]
    m1.compte.set_password("NouveauMdp!2026")
    m1.compte.save()
    corriger_integration(
        membre=m1, annee=2016, paroisse=monde["P1"], motif="Année erronée", par=compte_technique
    )
    m1.refresh_from_db()
    requete = RequestFactory().post("/connexion/")
    assert authenticate(requete, username=m1.matricule, password="NouveauMdp!2026") == m1.compte


@pytest.mark.parametrize(
    "kw, attendu",
    [
        (dict(motif=""), "motif"),
        (dict(annee=1800), "année"),
        (dict(annee=2015, paroisse=None), "modification"),
    ],
)
def test_motif_obligatoire(monde, compte_technique, kw, attendu):
    m1 = monde["m1"]
    args = dict(membre=m1, annee=2016, paroisse=monde["P1"], motif="x", par=compte_technique)
    args.update(kw)
    if args["paroisse"] is None:
        args["paroisse"] = monde["P1"]
    with pytest.raises(CorrectionRefusee, match=attendu):
        corriger_integration(**args)


def test_parcours_non_touche_si_mute(monde, compte_technique):
    m1 = monde["m1"]
    mut = demander_mutation(membre=m1, paroisse_arrivee=monde["P2"], par=compte_technique)
    decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=date(2026, 1, 1))
    corriger_integration(
        membre=m1, annee=2015, paroisse=monde["P3"], motif="Erreur", par=compte_technique
    )
    premiere = m1.affectations.order_by("date_debut", "pk").first()
    assert premiere.paroisse == monde["P1"]


def test_page_reservee_au_bn(client, client_technique, monde):
    m1 = monde["m1"]
    url = f"/membres/bn/{m1.matricule}/corriger/"
    client.force_login(monde["sec_p1"].compte)
    assert client.get(url).status_code == 403
    assert url in client_technique.get(f"/membres/bn/{m1.matricule}/").content.decode()
    r = client_technique.post(url, {"annee": "2016", "paroisse": monde["P4"].pk, "motif": "Reçu"})
    m1.refresh_from_db()
    assert r.status_code == 302 and r.url == f"/membres/bn/{m1.matricule}/"
    assert m1.matricule.startswith("2016-05AS-")
    r = client_technique.post(
        f"/membres/bn/{m1.matricule}/corriger/",
        {"annee": "2016", "paroisse": monde["P4"].pk, "motif": ""},
    )
    assert r.status_code == 200
