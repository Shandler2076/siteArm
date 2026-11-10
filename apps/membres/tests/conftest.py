import pytest
from django.contrib.auth.models import Permission

from apps.comptes.models import Compte


@pytest.fixture
def paroisse(db):
    from apps.organisation.models import Circuit, Paroisse, Region

    r = Region.objects.create(code="03", nom="HOULENOU")
    return Paroisse.objects.create(
        circuit=Circuit.objects.create(region=r, nom="Ekpe A"), nom="P1"
    )


@pytest.fixture
def compte_bn(db):
    c = Compte.objects.create_user("BN1", "MotDePasse!2026", doit_changer_mot_de_passe=False)
    c.user_permissions.add(
        *Permission.objects.filter(codename__in=["gerer_membres", "voir_cip"])
    )
    return c


@pytest.fixture
def bn(client, compte_bn):
    client.force_login(compte_bn)
    return compte_bn


@pytest.fixture
def client_bn(client, compte_bn):
    client.force_login(compte_bn)
    return client


@pytest.fixture
def admin_client_tech(client, db):
    client.force_login(Compte.objects.create_superuser("tech", "MotDePasse!2026"))
    return client


@pytest.fixture
def membre_enregistre(paroisse, compte_bn):
    import datetime

    from apps.membres.services import enregistrer_membre

    return enregistrer_membre(
        donnees={
            "nom": "Hounkpè", "prenoms": "Jean-Marc", "sexe": "M", "telephone": "0197000000",
            "date_naissance": datetime.date(1990, 5, 1), "categorie": "actif",
        },
        paroisse_integration=paroisse, annee_integration=2015, par=compte_bn,
    )
