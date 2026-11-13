import datetime
import io

import pytest
from django.core.management import call_command
from django.test import Client

from apps.cotisations.models import EtatVersement, ParametresCotisations, Tarif, Versement

D = datetime.date


def test_reglages_bn_seulement(monde, client_technique):
    c = Client()
    c.force_login(monde["sec_p1"].compte)
    assert c.get("/cotisations/bn/reglages/").status_code == 403
    assert client_technique.get("/cotisations/bn/reglages/").status_code == 200
    r = client_technique.post(
        "/cotisations/bn/reglages/", {"action": "depart", "mois_depart": "2027-01-01"}
    )
    assert r.status_code == 302 and ParametresCotisations.courant().mois_depart == D(2027, 1, 1)


def test_reglage_tarif_total_100(db, client_technique):
    donnees = {
        "action": "tarif",
        "date_effet": "2027-01-01",
        "montant": "150",
        "part_paroisse": "30",
        "part_circuit": "20",
        "part_region": "20",
        "part_national": "20",
    }
    r = client_technique.post("/cotisations/bn/reglages/", donnees)
    assert r.status_code == 200 and "100 %" in r.content.decode() and not Tarif.objects.exists()
    r = client_technique.post("/cotisations/bn/reglages/", donnees | {"part_national": "30"})
    assert r.status_code == 302 and Tarif.objects.get().montant == 150


def test_commande_rappel(monde, depart):
    from django.utils import timezone

    from apps.cotisations.services import saisir_versement
    from apps.cotisations.tests.conftest import enregistre_le

    enregistre_le(monde["m1"], D(2025, 1, 1))
    v = saisir_versement(monde["m1"], montant=100, date_versement=D(2026, 1, 5), par=None)
    Versement.objects.filter(pk=v.pk).update(
        date_saisie=timezone.now() - datetime.timedelta(days=40)
    )
    sortie = io.StringIO()
    call_command("rappel_cotisations", forcer=True, stdout=sortie)
    assert "1 versement" in sortie.getvalue()


def test_demo_cotisations_variees(territoire, settings):
    settings.SITE_DEMO = True
    call_command("peupler_demo", membres=60, stdout=io.StringIO())
    assert ParametresCotisations.courant().mois_depart is not None
    etats = set(Versement.objects.values_list("etat", flat=True))
    assert {EtatVersement.VALIDE, EtatVersement.EN_ATTENTE, EtatVersement.REFUSE} <= etats
    from apps.cotisations.regles import situations
    from apps.membres.models import Membre

    sits = situations(Membre.objects.all(), timezone_mois())
    assert any(s.a_jour for s in sits.values()) and any(s.retard >= 2 for s in sits.values())


def timezone_mois():
    from django.utils import timezone

    return timezone.localdate().replace(day=1)


@pytest.fixture
def depart(db):
    p = ParametresCotisations.courant()
    p.mois_depart = D(2026, 1, 1)
    p.save()
    return p.mois_depart
