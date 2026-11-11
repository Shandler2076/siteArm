import io

import pytest
from django.core.management import CommandError, call_command

from apps.bureaux.perimetre import est_bn, unites_gerees
from apps.comptes.models import Compte
from apps.membres.models import Membre


def _lancer(**kw):
    sortie = io.StringIO()
    call_command("peupler_demo", stdout=sortie, **kw)
    return sortie.getvalue()


def test_refuse_hors_site_d_essai(territoire, settings):
    settings.SITE_DEMO = False
    with pytest.raises(CommandError, match="site d'essai"):
        _lancer()
    assert not Membre.objects.exists()


def test_refuse_sans_territoire(db, settings):
    settings.SITE_DEMO = True
    with pytest.raises(CommandError, match="territoire"):
        _lancer()


def test_peuple_et_affiche_les_comptes(territoire, settings):
    settings.SITE_DEMO = True
    sortie = _lancer(membres=40)
    assert Membre.objects.count() >= 40
    assert "Mot de passe" in sortie and "Secrétaire national" in sortie
    comptes = {c.identifiant: c for c in Compte.objects.all()}
    bn = [c for c in comptes.values() if est_bn(c)]
    assert len(bn) == 2
    gestion = [c for c in comptes.values() if unites_gerees(c)]
    assert {u.niveau for c in gestion for u in unites_gerees(c)} >= {
        "paroisse",
        "circuit",
        "region",
        "national",
    }
    for c in bn:
        assert c.identifiant in sortie
    assert Membre.objects.exclude(statut="actif").exists()
    with pytest.raises(CommandError, match="déjà"):
        _lancer(membres=5)
