"""Faille faible : l'administration technique contourne les règles du site (journal, services).
Sur le vrai site, elle est en lecture seule ; fermer ou rouvrir une unité reste possible."""

import pytest

from apps.organisation.models import Region


@pytest.fixture
def tech(client, db, settings):
    settings.DOUBLE_VERIFICATION_BN = False  # sujet de ce fichier : la gestion seulement
    from apps.comptes.models import Compte

    c = Compte.objects.create_superuser(identifiant="tech", password="x" * 12)
    client.force_login(c)
    return client


@pytest.fixture
def region(db):
    return Region.objects.create(code="99", nom="Essai")


def test_lecture_seule(tech, region, settings):
    settings.ADMIN_LECTURE_SEULE = True
    assert tech.get("/gestion/organisation/region/add/").status_code == 403
    page = tech.get(f"/gestion/organisation/region/{region.pk}/change/")
    assert page.status_code == 200 and 'name="_save"' not in page.content.decode()
    r = tech.post(f"/gestion/organisation/region/{region.pk}/change/", {"code": "99", "nom": "X"})
    region.refresh_from_db()
    assert region.nom == "Essai" and r.status_code == 403


def test_fermer_reste_possible(tech, region, settings):
    settings.ADMIN_LECTURE_SEULE = True
    tech.post(
        "/gestion/organisation/region/",
        {"action": "fermer_selection", "_selected_action": [region.pk]},
    )
    region.refresh_from_db()
    assert not region.active


def test_modifiable_quand_l_interrupteur_est_ouvert(tech, settings):
    settings.ADMIN_LECTURE_SEULE = False
    assert tech.get("/gestion/organisation/region/add/").status_code == 200
