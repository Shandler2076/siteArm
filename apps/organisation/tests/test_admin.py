import pytest

from apps.organisation.models import Region


@pytest.fixture
def admin_client_bn(client, db):
    from apps.comptes.models import Compte

    client.force_login(Compte.objects.create_superuser("tech", "MotDePasse!2026"))
    return client


def test_liste_regions_accessible(admin_client_bn):
    Region.objects.create(code="01", nom="PORTO-NOVO")
    r = admin_client_bn.get("/gestion/organisation/region/")
    assert r.status_code == 200 and "PORTO-NOVO" in r.content.decode()


def test_titre_en_francais(admin_client_bn):
    assert "Armée du Salut — Gestion" in admin_client_bn.get("/gestion/").content.decode()


def test_pas_de_suppression_dans_admin(admin_client_bn):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    r = admin_client_bn.get(f"/gestion/organisation/region/{reg.pk}/delete/")
    assert r.status_code == 403


def test_action_fermer(admin_client_bn):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    admin_client_bn.post(
        "/gestion/organisation/region/",
        {"action": "fermer_selection", "_selected_action": [reg.pk]},
    )
    reg.refresh_from_db()
    assert reg.active is False


def test_code_non_modifiable_apres_creation(admin_client_bn):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    r = admin_client_bn.get(f"/gestion/organisation/region/{reg.pk}/change/")
    assert 'name="code"' not in r.content.decode()
