import datetime

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError

from apps.membres.models import Affectation, Categorie, Membre, Statut


@pytest.fixture
def paroisse(db):
    from apps.organisation.models import Circuit, Paroisse, Region

    r = Region.objects.create(code="01", nom="PORTO-NOVO")
    return Paroisse.objects.create(circuit=Circuit.objects.create(region=r, nom="Davo"), nom="P1")


def _membre(paroisse, **kw):
    d = dict(
        nom="Hounkpè",
        prenoms="Jean-Marc",
        sexe="M",
        telephone="0197000000",
        annee_integration=2015,
        paroisse_integration=paroisse,
        region_integration=paroisse.region,
        matricule="2015-01AS-0001",
    )
    d.update(kw)
    return Membre.objects.create(**d)


def test_valeurs_par_defaut(paroisse):
    m = _membre(paroisse)
    assert m.categorie == Categorie.ACTIF and m.statut == Statut.ACTIF
    assert m.get_categorie_display() == "Membre actif"


def test_nom_complet_et_age(paroisse):
    m = _membre(paroisse, date_naissance=datetime.date(2000, 11, 11))
    assert m.nom_complet == "HOUNKPÈ Jean-Marc"
    assert m.age(datetime.date(2026, 11, 10)) == 25
    assert m.age(datetime.date(2026, 11, 11)) == 26
    assert _membre(paroisse, matricule="2015-01AS-0002").age() is None


def test_npi_unique_si_renseigne(paroisse):
    _membre(paroisse, npi="", matricule="2015-01AS-0001")
    _membre(paroisse, npi="", matricule="2015-01AS-0002")
    _membre(paroisse, npi="1234567890", matricule="2015-01AS-0003")
    with pytest.raises(IntegrityError):
        _membre(paroisse, npi="1234567890", matricule="2015-01AS-0004")


@pytest.mark.parametrize("annee", [1899, datetime.date.today().year + 1])
def test_annee_integration_invalide(paroisse, annee):
    m = Membre(
        nom="A",
        prenoms="B",
        sexe="F",
        telephone="0197000000",
        annee_integration=annee,
        paroisse_integration=paroisse,
        region_integration=paroisse.region,
        matricule="X",
    )
    with pytest.raises(ValidationError):
        m.full_clean()


def test_une_seule_affectation_ouverte(paroisse):
    m = _membre(paroisse)
    kw = dict(
        membre=m,
        paroisse=paroisse,
        circuit_a_date=paroisse.circuit,
        region_a_date=paroisse.region,
        date_debut=datetime.date(2015, 1, 1),
        motif="Intégration",
    )
    Affectation.objects.create(**kw)
    with pytest.raises(IntegrityError):
        Affectation.objects.create(**kw)


def test_suppression_interdite(paroisse):
    with pytest.raises(PermissionDenied):
        _membre(paroisse).delete()
