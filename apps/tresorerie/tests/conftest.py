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
def ouvert(db):
    """Cotisations ouvertes depuis le mois en cours (100 F par mois, 30/20/20/30)."""
    from django.utils import timezone

    from apps.cotisations.models import ParametresCotisations

    p = ParametresCotisations.courant()
    p.mois_depart = timezone.localdate().replace(day=1)
    p.save()
    return p


@pytest.fixture
def tresoriers(monde, nouveau_membre, donner_mandat):
    """Trésorier de P1 (déjà dans `monde`), Trésorier national, Président."""
    d = datetime.date(2025, 1, 1)
    tn = nouveau_membre(monde["P2"], "TresNat")
    donner_mandat(tn, "Trésorier national", debut=d)
    pres = nouveau_membre(monde["P3"], "Pres")
    donner_mandat(pres, "Président", debut=d)
    return dict(monde, tresorier_national=tn, president=pres)
