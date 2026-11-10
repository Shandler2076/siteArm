import pytest

from apps.comptes.models import Compte


@pytest.mark.django_db
def test_create_user_normalise_identifiant_et_exige_changement():
    c = Compte.objects.create_user(" 2015-01as-0157 ", "MotDePasse!2026")
    assert c.identifiant == "2015-01AS-0157"
    assert c.doit_changer_mot_de_passe is True
    assert c.check_password("MotDePasse!2026")


@pytest.mark.django_db
def test_create_superuser():
    c = Compte.objects.create_superuser("tech", "MotDePasse!2026")
    assert c.is_staff and c.is_superuser
    assert c.doit_changer_mot_de_passe is False
