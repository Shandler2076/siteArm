from datetime import date

import pytest

from apps.listes.ages import date_limite, filtrer_age, tranches_depuis_bornes
from apps.listes.models import ReglageStatistiques
from apps.membres.models import Membre

J = date(2026, 11, 10)


@pytest.fixture
def membre(territoire, nouveau_membre):
    def fabriquer(naissance):
        m = nouveau_membre(territoire["P1"], "Age")
        m.date_naissance = naissance
        m.save()
        return m

    return fabriquer


def _dans(m, condition, x=None, y=None, j=J):
    return filtrer_age(Membre.objects.all(), condition, x, y, j).filter(pk=m.pk).exists()


@pytest.mark.parametrize(
    "naissance, age, moins18, entre18_40, plus40",
    [
        (date(2008, 11, 11), 17, True, False, False),
        (date(2008, 11, 10), 18, False, True, False),
        (date(1986, 11, 10), 40, False, True, False),
        (date(1985, 11, 11), 40, False, True, False),
        (date(1985, 11, 10), 41, False, False, True),
    ],
)
def test_bornes_exactes(membre, naissance, age, moins18, entre18_40, plus40):
    m = membre(naissance)
    assert m.age(J) == age
    assert _dans(m, "moins", 18) is moins18
    assert _dans(m, "entre", 18, 40) is entre18_40
    assert _dans(m, "plus", 40) is plus40


def test_29_fevrier(membre):
    m = membre(date(2008, 2, 29))
    for j in [date(2026, 2, 28), date(2026, 3, 1)]:
        assert _dans(m, "plus", 17, j=j) is (m.age(j) > 17)
    assert not _dans(m, "plus", 17, j=date(2026, 2, 28))
    assert _dans(m, "plus", 17, j=date(2026, 3, 1))
    j = date(2028, 2, 29)
    a = membre(date(2010, 2, 28))
    b = membre(date(2010, 3, 1))
    assert a.age(j) == 18 and _dans(a, "entre", 18, 18, j=j)
    assert b.age(j) == 17 and _dans(b, "moins", 18, j=j)
    assert date_limite(j, 18) == date(2010, 2, 28)


def test_inconnu_et_exclusion(membre):
    m = membre(None)
    assert _dans(m, "inconnu")
    assert not _dans(m, "moins", 130)
    assert not _dans(m, "plus", 0)
    assert not _dans(m, "entre", 0, 130)
    assert not _dans(membre(date(2000, 1, 1)), "inconnu")


def test_tranches_par_defaut(db):
    bornes = ReglageStatistiques.courant().liste_bornes
    assert [t.libelle for t in tranches_depuis_bornes(bornes)] == [
        "Moins de 18 ans",
        "18 à 40 ans",
        "Plus de 40 ans",
    ]


def test_tranches_trois_bornes():
    assert [(t.condition, t.x, t.y) for t in tranches_depuis_bornes([18, 40, 60])] == [
        ("moins", 18, None),
        ("entre", 18, 40),
        ("entre", 41, 60),
        ("plus", 60, None),
    ]
    assert tranches_depuis_bornes([18, 40, 60])[2].libelle == "41 à 60 ans"


def test_une_seule_borne():
    assert [(t.libelle, t.condition, t.x) for t in tranches_depuis_bornes([18])] == [
        ("Moins de 18 ans", "moins", 18),
        ("18 ans et plus", "plus", 17),
    ]


@pytest.mark.parametrize("bornes", [[18], [1], [18, 40], [18, 19], [5, 18, 40, 60, 80, 120]])
def test_tranches_couvrent_tout_le_monde(membre, bornes):
    autour = {0, 124} | {b + d for b in bornes for d in (-1, 0, 1)}
    for annees in sorted(a for a in autour if a >= 0):
        membre(date(2026 - annees, 11, 10))
        membre(date(2026 - annees, 11, 11))  # un jour avant l'anniversaire
    nes = Membre.objects.all()
    total = 0
    for t in tranches_depuis_bornes(bornes):
        total += filtrer_age(nes, t.condition, t.x, t.y, J).count()
    assert total == nes.count()
