import datetime

import pytest
from django.core.exceptions import ValidationError

from apps.bureaux.models import Fonction, Mandat, Niveau


def test_fonctions_du_reglement_chargees(db):
    gerent = set(Fonction.objects.filter(droit_gerer=True).values_list("nom", flat=True))
    assert gerent == {
        "Chef d'Unité paroissiale",
        "Secrétaire paroissial",
        "Chef de Section de Circuit",
        "Secrétaire de Circuit",
        "Coordinateur régional",
        "Secrétaire régional",
        "Président",
        "Secrétaire national",
    }
    assert Fonction.objects.filter(niveau=Niveau.NATIONAL).count() == 13
    assert Fonction.objects.filter(niveau=Niveau.REGION, membre_du_bureau=True).count() == 9
    assert Fonction.objects.filter(niveau=Niveau.PAROISSE).count() == 3
    assert Fonction.objects.filter(niveau=Niveau.CIRCUIT, membre_du_bureau=True).count() == 5
    assert Fonction.objects.get(nom="Président").duree_mandat_annees == 4
    assert Fonction.objects.get(nom="Secrétaire paroissial").duree_mandat_annees == 2
    assert Fonction.objects.get(nom="Vérificateur de Circuit").droit_gerer is False


def test_date_fin_prevue_calculee(territoire, nouveau_membre, donner_mandat):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    mandat = donner_mandat(
        m, "Secrétaire paroissial", territoire["P1"], debut=datetime.date(2024, 2, 29)
    )
    assert mandat.date_fin_prevue == datetime.date(2026, 2, 28)


def test_unite_doit_correspondre_au_niveau(territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    f = Fonction.objects.get(nom="Secrétaire paroissial")
    with pytest.raises(ValidationError, match="niveau de la fonction"):
        Mandat(
            membre=m, fonction=f, circuit=territoire["Ekpe A"], date_debut=datetime.date(2026, 1, 1)
        ).full_clean()


def test_mandat_national_sans_unite(territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    f = Fonction.objects.get(nom="Président")
    Mandat(membre=m, fonction=f, date_debut=datetime.date(2026, 1, 1)).full_clean()
    with pytest.raises(ValidationError):
        Mandat(
            membre=m, fonction=f, region=territoire["WEME"], date_debut=datetime.date(2026, 1, 1)
        ).full_clean()


@pytest.mark.parametrize(
    "debut,fin,attendu",
    [
        (datetime.date(2026, 1, 1), None, True),
        (datetime.date(2026, 11, 11), None, False),
        (datetime.date(2026, 1, 1), datetime.date(2026, 11, 10), False),
        (datetime.date(2026, 1, 1), datetime.date(2026, 11, 11), True),
    ],
)
def test_est_en_cours(territoire, nouveau_membre, donner_mandat, debut, fin, attendu):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    mandat = donner_mandat(m, "Secrétaire paroissial", territoire["P1"], debut=debut, fin=fin)
    assert mandat.est_en_cours(datetime.date(2026, 11, 10)) is attendu
    assert (mandat in Mandat.objects.en_cours(datetime.date(2026, 11, 10))) is attendu
