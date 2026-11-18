# ruff: noqa: F811 — fixtures importées de apps/bureaux/tests/conftest.py
import datetime

import pytest

from apps.bureaux.tests.conftest import (  # noqa: F401
    client_technique,
    compte_technique,
    donner_mandat,
    monde,
    nouveau_membre,
    territoire,
)


@pytest.fixture
def bn(monde, nouveau_membre, donner_mandat):
    """Président et Secrétaire national, Chef d'Unité paroissiale de P1 (en plus de `monde`)."""
    d = datetime.date(2025, 1, 1)
    pres = nouveau_membre(monde["P3"], "Pres")
    donner_mandat(pres, "Président", debut=d)
    sn = nouveau_membre(monde["P4"], "Secnat")
    donner_mandat(sn, "Secrétaire national", debut=d)
    chef_p1 = nouveau_membre(monde["P1"], "Chefp")
    donner_mandat(chef_p1, "Chef d'Unité paroissiale", monde["P1"], debut=d)
    return dict(monde, president=pres, sn=sn, chef_p1=chef_p1)


def image_signature(nom="signature.png"):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    sortie = io.BytesIO()
    Image.new("RGB", (400, 160), "white").save(sortie, "PNG")
    return SimpleUploadedFile(nom, sortie.getvalue(), content_type="image/png")


@pytest.fixture(autouse=True)
def _apres_validation_immediate(monkeypatch):
    """Les notifications partent après la transaction : dans les tests, tout de suite."""
    monkeypatch.setattr("django.db.transaction.on_commit", lambda f, *a, **k: f())
