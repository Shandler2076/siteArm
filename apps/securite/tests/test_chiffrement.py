"""Clés de double vérification chiffrées dans la base et dans les sauvegardes (dumpdata)."""

import io

import pytest
from django.core.management import call_command
from django.db import connection

from apps.securite.models import DoubleVerification

SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


@pytest.fixture
def dv(compte_technique):
    return DoubleVerification.objects.create(compte=compte_technique, secret=SECRET, active=True)


def _brut(pk):
    with connection.cursor() as c:
        c.execute("SELECT secret FROM securite_doubleverification WHERE id = %s", [pk])
        return c.fetchone()[0]


def test_chiffree_en_base_lisible_par_le_site(dv):
    brut = _brut(dv.pk)
    assert SECRET not in brut and brut.startswith("chiffre:")
    assert DoubleVerification.objects.get(pk=dv.pk).secret == SECRET


def test_sauvegarde_sans_cle_en_clair(dv):
    sortie = io.StringIO()
    call_command("dumpdata", "securite.doubleverification", stdout=sortie)
    assert SECRET not in sortie.getvalue()


def test_ancienne_cle_en_clair_reste_lisible_puis_chiffree(dv):
    from apps.securite.chiffrement import chiffrer_les_cles_existantes

    with connection.cursor() as c:
        c.execute(
            "UPDATE securite_doubleverification SET secret = %s WHERE id = %s", [SECRET, dv.pk]
        )
    assert DoubleVerification.objects.get(pk=dv.pk).secret == SECRET
    chiffrer_les_cles_existantes(DoubleVerification)
    assert _brut(dv.pk).startswith("chiffre:")
    assert DoubleVerification.objects.get(pk=dv.pk).secret == SECRET


def test_cle_illisible_ne_plante_pas(dv, settings):
    settings.CLE_DOUBLE_VERIFICATION = "une-autre-cle-de-chiffrement"
    assert DoubleVerification.objects.get(pk=dv.pk).secret == ""
