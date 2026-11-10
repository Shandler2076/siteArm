from datetime import date
from urllib.parse import urlencode

import pytest
from django.http import QueryDict

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.listes.filtres import FiltreListeForm, membres_filtres
from apps.listes.statistiques import calculer_statistiques

J = date(2026, 11, 10)


def _sections(unite, statuts=("actif",)):
    return {s.titre: s for s in calculer_statistiques(unite, list(statuts), J)}


def _chiffres(section):
    return {c.libelle: c.nombre for c in section.cellules}


@pytest.fixture
def varies(monde):
    m1, m2, m3 = monde["m1"], monde["m2"], monde["m3"]
    m1.sexe, m1.date_naissance, m1.categorie = "F", date(2010, 1, 1), "honneur"
    m1.save()
    m2.date_naissance = date(1990, 1, 1)
    m2.save()
    m3.date_naissance = date(1970, 1, 1)
    m3.statut = "decede"
    m3.save()
    return monde


def test_totaux(varies):
    s = _sections(Unite(Niveau.PAROISSE, varies["P1"]))
    assert list(s) == [
        "Total",
        "Par sexe",
        "Par tranche d'âge",
        "Par catégorie",
        "Par statut",
    ]
    assert _chiffres(s["Total"]) == {"Total des membres": 3}
    assert _chiffres(s["Par sexe"]) == {"Hommes": 2, "Femmes": 1}
    assert _chiffres(s["Par catégorie"]) == {
        "Membre actif": 2,
        "Membre d'honneur": 1,
        "Membre sympathisant": 0,
    }


def test_tranches_et_age_inconnu(varies):
    s = _sections(Unite(Niveau.NATIONAL, None))
    assert _chiffres(s["Par tranche d'âge"]) == {
        "Moins de 18 ans": 1,
        "18 à 40 ans": 1,
        "Plus de 40 ans": 0,
        "Âge non renseigné": 4,
    }
    assert (
        sum(_chiffres(s["Par tranche d'âge"]).values())
        == _chiffres(s["Total"])["Total des membres"]
    )


def test_statut_selectionnable(varies):
    s = _sections(Unite(Niveau.NATIONAL, None), ["decede"])
    assert _chiffres(s["Total"]) == {"Total des membres": 1}
    assert _chiffres(s["Par tranche d'âge"])["Plus de 40 ans"] == 1
    statuts = _chiffres(s["Par statut"])
    assert statuts == _chiffres(_sections(Unite(Niveau.NATIONAL, None))["Par statut"])
    assert statuts["Actif"] == 6 and statuts["Décédé"] == 1 and statuts["Exclu"] == 0
    tous = _sections(Unite(Niveau.NATIONAL, None), [])
    assert _chiffres(tous["Total"]) == {"Total des membres": 7}


def test_repartition(monde):
    assert _chiffres(_sections(Unite(Niveau.NATIONAL, None))["Par région"]) == {
        "03 — HOULENOU": 6,
        "05 — WEME": 1,
    }
    assert _chiffres(_sections(Unite(Niveau.REGION, monde["HOULENOU"]))["Par circuit"]) == {
        "Ekpe A": 5,
        "Ekpe B": 1,
    }
    assert _chiffres(_sections(Unite(Niveau.CIRCUIT, monde["Ekpe A"]))["Par paroisse"]) == {
        "P1": 3,
        "P2": 2,
    }


def test_repartition_unite_fermee(monde):
    monde["P2"].fermer()
    vide_fermee = monde["Ekpe B"]
    for m in [monde["m3"]]:
        a = m.affectations.get()
        a.paroisse = monde["P1"]
        a.save()
    vide_fermee.fermer()
    circuits = _chiffres(_sections(Unite(Niveau.REGION, monde["HOULENOU"]))["Par circuit"])
    assert "Ekpe B" not in circuits  # fermé et vide
    assert _chiffres(_sections(Unite(Niveau.CIRCUIT, monde["Ekpe A"]))["Par paroisse"]) == {
        "P1": 4,
        "P2 (fermée)": 2,
    }


def test_repartition_sans_affectation(monde):
    a = monde["m1"].affectations.get()
    a.date_fin = J
    a.save()
    s = _chiffres(_sections(Unite(Niveau.NATIONAL, None))["Par région"])
    assert s["Sans affectation"] == 1 and s["03 — HOULENOU"] == 5
    assert "Sans affectation" not in _chiffres(
        _sections(Unite(Niveau.REGION, monde["HOULENOU"]))["Par circuit"]
    )


def test_chiffre_egal_liste(varies):
    a = varies["m4"].affectations.get()
    a.date_fin = J
    a.save()
    t = varies
    unites = [
        Unite(Niveau.NATIONAL, None),
        Unite(Niveau.REGION, t["HOULENOU"]),
        Unite(Niveau.REGION, t["WEME"]),
        Unite(Niveau.CIRCUIT, t["Ekpe A"]),
        Unite(Niveau.PAROISSE, t["P1"]),
    ]
    for unite in unites:
        for statuts in (["actif"], [], ["decede", "actif"]):
            for section in calculer_statistiques(unite, statuts, J):
                for c in section.cellules:
                    form = FiltreListeForm(unite, QueryDict(urlencode(c.filtres, doseq=True)))
                    assert form.is_valid(), (unite, c, form.errors)
                    n = membres_filtres(unite, form.cleaned_data, J).count()
                    assert n == c.nombre, (unite.cle, statuts, c)
