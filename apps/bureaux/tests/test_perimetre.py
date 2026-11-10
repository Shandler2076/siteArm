import datetime

import pytest
from django.http import Http404

from apps.bureaux import perimetre as P

AUJ = datetime.date(2026, 11, 10)


def _noms(qs):
    return {m.nom for m in qs}


def test_perimetres(monde):
    p1 = P.Unite("paroisse", monde["P1"])
    ca = P.Unite("circuit", monde["Ekpe A"])
    reg = P.Unite("region", monde["HOULENOU"])
    nat = P.Unite("national", None)
    assert _noms(P.membres_visibles(p1)) == {"Adjovi", "Secretaire", "Tresorier"}
    assert _noms(P.membres_visibles(ca)) == {"Adjovi", "Bio", "Secretaire", "Chef", "Tresorier"}
    assert "Chabi" in _noms(P.membres_visibles(reg))
    assert "Dossou" not in _noms(P.membres_visibles(reg))
    assert P.membres_visibles(nat).count() == 7


def test_cle_et_libelle(monde):
    u = P.Unite("paroisse", monde["P1"])
    assert u.cle == f"paroisse-{monde['P1'].pk}" and u.libelle == "Paroisse P1"
    assert P.Unite("circuit", monde["Ekpe A"]).libelle == "Circuit Ekpe A"
    assert P.Unite("region", monde["WEME"]).libelle == "Région WEME"
    assert P.Unite("national", None).cle == "national"
    assert P.Unite("national", None).libelle == "Bureau National de Commandement"


def test_seules_les_fonctions_de_gestion_comptent(monde):
    assert [u.cle for u in P.unites_gerees(monde["sec_p1"].compte, AUJ)] == [
        f"paroisse-{monde['P1'].pk}"
    ]
    assert P.unites_gerees(monde["tresorier"].compte, AUJ) == []
    assert P.unites_gerees(monde["m1"].compte, AUJ) == []


def test_compte_sans_membre(compte_technique, monde):
    assert P.unites_gerees(compte_technique, AUJ) == []
    assert P.est_bn(compte_technique)


def test_bornes_des_dates(monde, donner_mandat):
    m = monde["m3"]
    donner_mandat(m, "Secrétaire paroissial", monde["P3"], debut=datetime.date(2026, 11, 11))
    assert P.unites_gerees(m.compte, AUJ) == []
    donner_mandat(
        monde["m4"], "Secrétaire paroissial", monde["P4"], debut=datetime.date(2024, 1, 1), fin=AUJ
    )
    assert P.unites_gerees(monde["m4"].compte, AUJ) == []


def test_titulaire_sanctionne_perd_ses_droits(monde):
    sec = monde["sec_p1"]
    sec.statut = "sanctionne"
    sec.save()
    assert P.unites_gerees(sec.compte, AUJ) == []


def test_est_bn(monde, donner_mandat):
    assert not P.est_bn(monde["sec_p1"].compte, AUJ)
    donner_mandat(monde["m1"], "Président", None, debut=datetime.date(2025, 1, 1))
    assert P.est_bn(monde["m1"].compte, AUJ)
    donner_mandat(monde["m2"], "Trésorier national", None, debut=datetime.date(2025, 1, 1))
    assert not P.est_bn(monde["m2"].compte, AUJ)


def test_reorganisation_du_territoire(monde):
    p2 = monde["P2"]
    p2.circuit = monde["Ekpe B"]
    p2.save()
    ca = P.Unite("circuit", monde["Ekpe A"])
    cb = P.Unite("circuit", monde["Ekpe B"])
    assert "Bio" not in _noms(P.membres_visibles(ca))
    assert "Bio" in _noms(P.membres_visibles(cb))


def test_plusieurs_mandats_s_additionnent(monde, donner_mandat):
    sec = monde["sec_p1"]
    donner_mandat(sec, "Coordinateur régional", monde["WEME"], debut=datetime.date(2025, 1, 1))
    assert {u.niveau for u in P.unites_gerees(sec.compte, AUJ)} == {"paroisse", "region"}
    assert P.peut_voir_membre(sec.compte, monde["m4"])
    assert P.peut_voir_membre(sec.compte, monde["m1"])
    assert not P.peut_voir_membre(sec.compte, monde["m3"])


def test_membre_simple_ne_voit_que_lui(monde):
    assert P.peut_voir_membre(monde["m1"].compte, monde["m1"])
    assert not P.peut_voir_membre(monde["m1"].compte, monde["m2"])


def test_unite_depuis_cle(monde):
    c = monde["sec_p1"].compte
    assert P.unite_depuis_cle(c, f"paroisse-{monde['P1'].pk}").objet == monde["P1"]
    for cle in [
        f"paroisse-{monde['P2'].pk}",
        f"circuit-{monde['Ekpe A'].pk}",
        "national",
        "paroisse-x",
        "nimporte",
        "paroisse-999999",
    ]:
        with pytest.raises(Http404):
            P.unite_depuis_cle(c, cle)


def test_bn_ouvre_toute_unite(monde, compte_technique):
    assert (
        P.unite_depuis_cle(compte_technique, f"circuit-{monde['Ekpe B'].pk}").objet
        == monde["Ekpe B"]
    )
    with pytest.raises(Http404):
        P.unite_depuis_cle(compte_technique, "circuit-999999")


def test_titulaires_gestion(monde):
    assert list(P.titulaires_gestion(P.Unite("paroisse", monde["P1"]))) == [monde["sec_p1"].compte]
    assert list(P.titulaires_gestion(P.Unite("circuit", monde["Ekpe A"]))) == [monde["chef"].compte]


def test_anciens_membres(monde):
    from apps.membres.models import Affectation

    m1 = monde["m1"]
    a = m1.affectation_actuelle
    a.date_fin = AUJ
    a.save()
    Affectation.objects.create(
        membre=m1,
        paroisse=monde["P4"],
        circuit_a_date=monde["Dangbo A"],
        region_a_date=monde["WEME"],
        date_debut=AUJ,
        motif="Mutation",
    )
    anciens = P.anciens_membres(P.Unite("paroisse", monde["P1"]))
    assert [x.membre.nom for x in anciens] == ["Adjovi"]
    assert "Adjovi" not in _noms(P.membres_visibles(P.Unite("paroisse", monde["P1"])))
    assert list(P.anciens_membres(P.Unite("region", monde["WEME"]))) == []


def test_libelle_sans_doublon_paroisse(territoire):
    from apps.organisation.models import Paroisse

    p = Paroisse.objects.create(circuit=territoire["Ekpe A"], nom="Paroisse Saint Michel de X")
    assert P.Unite("paroisse", p).libelle == "Paroisse Saint Michel de X"

