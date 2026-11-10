import datetime

import pytest

from apps.comptes.models import Compte


@pytest.fixture
def compte_technique(db):
    return Compte.objects.create_superuser("tech", "MotDePasse!2026")


@pytest.fixture
def territoire(db):
    from apps.organisation.models import Circuit, Paroisse, Region

    t = {}
    t["HOULENOU"] = Region.objects.create(code="03", nom="HOULENOU")
    t["WEME"] = Region.objects.create(code="05", nom="WEME")
    t["Ekpe A"] = Circuit.objects.create(region=t["HOULENOU"], nom="Ekpe A")
    t["Ekpe B"] = Circuit.objects.create(region=t["HOULENOU"], nom="Ekpe B")
    t["Dangbo A"] = Circuit.objects.create(region=t["WEME"], nom="Dangbo A")
    t["P1"] = Paroisse.objects.create(circuit=t["Ekpe A"], nom="P1")
    t["P2"] = Paroisse.objects.create(circuit=t["Ekpe A"], nom="P2")
    t["P3"] = Paroisse.objects.create(circuit=t["Ekpe B"], nom="P3")
    t["P4"] = Paroisse.objects.create(circuit=t["Dangbo A"], nom="P4")
    return t


@pytest.fixture
def nouveau_membre(db, compte_technique):
    from apps.membres.services import enregistrer_membre

    def fabriquer(paroisse, nom, prenoms="Test"):
        m = enregistrer_membre(
            donnees={"nom": nom, "prenoms": prenoms, "sexe": "M", "telephone": "0197000000",
                     "categorie": "actif"},
            paroisse_integration=paroisse, annee_integration=2015, par=compte_technique,
        ).membre
        m.compte.doit_changer_mot_de_passe = False
        m.compte.save()
        return m

    return fabriquer


@pytest.fixture
def donner_mandat(db):
    from apps.bureaux.models import Fonction, Mandat

    def donner(membre, nom_fonction, unite=None, debut=None, fin=None):
        f = Fonction.objects.get(nom=nom_fonction)
        kw = {}
        if unite is not None:
            kw[f.niveau] = unite
        m = Mandat(membre=membre, fonction=f, date_debut=debut or datetime.date(2025, 1, 1),
                   date_fin=fin, **kw)
        m.full_clean()
        m.save()
        return m

    return donner
