import datetime

import pytest

from apps.comptes.models import Compte
from apps.organisation.models import Region


@pytest.fixture
def tech(db):
    return Compte.objects.create_superuser("tech", "MotDePasse!2026")


def test_connexion_admin_normalise_identifiant(client, tech):
    r = client.post("/gestion/login/", {"username": " tech ", "password": "MotDePasse!2026"})
    assert r.status_code == 302


def test_identifiant_normalise_a_l_enregistrement(db):
    c = Compte(identifiant=" 2015-01as-0999 ")
    c.set_password("MotDePasse!2026")
    c.save()
    assert c.identifiant == "2015-01AS-0999"


def test_compte_cree_dans_admin_peut_se_connecter(client, tech):
    client.force_login(tech)
    r = client.post(
        "/gestion/comptes/compte/add/",
        {
            "identifiant": "2015-01as-0999",
            "password1": "Provisoire!Salut26",
            "password2": "Provisoire!Salut26",
        },
    )
    assert r.status_code == 302, r.content.decode()[:2000]
    c = Compte.objects.get(identifiant="2015-01AS-0999")
    assert c.check_password("Provisoire!Salut26")
    assert c.doit_changer_mot_de_passe is True


def test_fermer_deux_fois_garde_la_date_d_origine(db):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    reg.fermer(datetime.date(2026, 12, 26))
    reg.fermer()
    reg.refresh_from_db()
    assert reg.date_fermeture == datetime.date(2026, 12, 26)
