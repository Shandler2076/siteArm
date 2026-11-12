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
from apps.lots.tests.conftest import classeur  # noqa: F401


@pytest.fixture
def depart(db):
    """Mois de départ des cotisations : janvier 2026."""
    from apps.cotisations.models import ParametresCotisations

    p = ParametresCotisations.courant()
    p.mois_depart = datetime.date(2026, 1, 1)
    p.save()
    return p.mois_depart


@pytest.fixture
def payer(db):
    """Crée directement un versement et ses mois (sans passer par les services)."""
    from apps.cotisations.models import EtatVersement, MoisCotise, Versement

    def creer(membre, mois, etat=EtatVersement.VALIDE, montant_mois=100):
        v = Versement.objects.create(
            membre=membre,
            paroisse=membre.affectation_actuelle.paroisse,
            montant=montant_mois * len(mois),
            date_versement=datetime.date(2026, 6, 1),
            etat=etat,
        )
        actif = etat in (EtatVersement.EN_ATTENTE, EtatVersement.VALIDE)
        for m in mois:
            MoisCotise.objects.create(
                versement=v, membre=membre, mois=m, montant=montant_mois, actif=actif
            )
        return v

    return creer


def enregistre_le(membre, jour):
    from django.utils import timezone

    from apps.membres.models import Membre

    Membre.objects.filter(pk=membre.pk).update(
        date_enregistrement=timezone.make_aware(datetime.datetime.combine(jour, datetime.time(9)))
    )
    membre.refresh_from_db()
    return membre
