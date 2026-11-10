import datetime

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError

from apps.organisation.models import Circuit, Paroisse, Region


@pytest.fixture
def paroisse(db):
    r = Region.objects.create(code="01", nom="PORTO-NOVO")
    c = Circuit.objects.create(region=r, nom="Davo")
    return Paroisse.objects.create(circuit=c, nom="Paroisse Saint Michel de TOKPOTA DAVO")


@pytest.mark.parametrize("code", ["1", "00", "100", "AB"])
def test_code_region_invalide(db, code):
    with pytest.raises(ValidationError):
        Region(code=code, nom="X").full_clean()


def test_code_region_unique(db):
    Region.objects.create(code="01", nom="PORTO-NOVO")
    with pytest.raises(IntegrityError):
        Region.objects.create(code="01", nom="AUTRE")


def test_paroisse_connait_sa_region(paroisse):
    assert paroisse.region.code == "01"


def test_suppression_interdite(paroisse):
    for obj in (paroisse, paroisse.circuit, paroisse.circuit.region):
        with pytest.raises(PermissionDenied):
            obj.delete()


def test_fermer_et_rouvrir(paroisse):
    paroisse.fermer(datetime.date(2026, 12, 26))
    paroisse.refresh_from_db()
    assert paroisse.active is False and paroisse.date_fermeture == datetime.date(2026, 12, 26)
    paroisse.rouvrir()
    paroisse.refresh_from_db()
    assert paroisse.active is True and paroisse.date_fermeture is None


def test_str(paroisse):
    assert str(paroisse.circuit.region) == "01 — PORTO-NOVO"
    assert str(paroisse.circuit) == "Circuit de Davo"
