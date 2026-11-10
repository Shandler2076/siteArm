import threading

import pytest
from django.db import connection, transaction

from apps.membres.models import CompteurMatricule
from apps.membres.services import CapaciteMatriculeAtteinte, attribuer_matricule
from apps.organisation.models import Region


@pytest.fixture
def region(db):
    return Region.objects.create(code="01", nom="PORTO-NOVO")


def _attribuer(annee, region):
    with transaction.atomic():
        return attribuer_matricule(annee, region)


def test_format_et_suite(region):
    assert _attribuer(2015, region) == "2015-01AS-0001"
    assert _attribuer(2015, region) == "2015-01AS-0002"


def test_compteurs_separes_par_annee_et_region(region):
    autre = Region.objects.create(code="02", nom="COTONOU")
    _attribuer(2015, region)
    assert _attribuer(2016, region) == "2016-01AS-0001"
    assert _attribuer(2015, autre) == "2015-02AS-0001"


def test_capacite_atteinte(region):
    CompteurMatricule.objects.create(annee=2015, region=region, dernier_numero=9999)
    with pytest.raises(CapaciteMatriculeAtteinte, match="9 999"):
        _attribuer(2015, region)
    assert CompteurMatricule.objects.get(annee=2015, region=region).dernier_numero == 9999


@pytest.mark.django_db(transaction=True)
def test_attributions_simultanees_sans_doublon():
    if connection.vendor != "postgresql":
        pytest.skip("Le verrou de ligne n'est vérifiable que sur PostgreSQL.")
    region = Region.objects.create(code="01", nom="PORTO-NOVO")
    resultats, erreurs = [], []

    def travail():
        try:
            resultats.append(_attribuer(2026, region))
        except Exception as e:  # noqa: BLE001
            erreurs.append(e)
        finally:
            connection.close()

    fils = [threading.Thread(target=travail) for _ in range(20)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert not erreurs
    assert sorted(resultats) == [f"2026-01AS-{i:04d}" for i in range(1, 21)]
