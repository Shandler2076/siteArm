"""Décision du 19/11/2026 : les mois dus partent de janvier (année d'intégration ou mois de
départ du BN), pas de la date d'inscription du membre sur le site."""

import datetime

from django.utils import timezone

from apps.cotisations.models import ParametresCotisations
from apps.cotisations.regles import mois_dus
from apps.cotisations.services import prochains_mois


def test_un_membre_inscrit_en_novembre_doit_depuis_janvier(monde):
    p = ParametresCotisations.courant()
    p.mois_depart = datetime.date(2026, 1, 1)
    p.save()
    m1 = monde["m1"]  # intégré en 2015, enregistré sur le site aujourd'hui
    jour = datetime.date(2026, 11, 15)
    assert mois_dus(m1, jour)[0] == datetime.date(2026, 1, 1)
    mois = prochains_mois(m1, 9, jour=jour)
    assert [m for m, _p in mois][0] == datetime.date(2026, 1, 1)
    assert [m for m, _p in mois][-1] == datetime.date(2026, 9, 1)  # 9 mois : janvier à septembre


def test_membre_integre_cette_annee_doit_depuis_janvier_de_son_annee(monde):
    p = ParametresCotisations.courant()
    p.mois_depart = datetime.date(2025, 1, 1)
    p.save()
    m1 = monde["m1"]
    m1.annee_integration = 2026
    m1.save(update_fields=["annee_integration"])
    assert mois_dus(m1, datetime.date(2026, 3, 1))[0] == datetime.date(2026, 1, 1)


def test_le_mois_de_depart_du_bn_reste_la_limite(monde):
    p = ParametresCotisations.courant()
    p.mois_depart = timezone.localdate().replace(day=1)
    p.save()
    assert mois_dus(monde["m1"], timezone.localdate())[0] == p.mois_depart
