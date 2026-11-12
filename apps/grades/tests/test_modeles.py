import pytest
from django.core.exceptions import PermissionDenied

from apps.membres.grades import Grade, grade_depuis_texte
from apps.membres.models import Membre

LIBELLES = [
    "Camarade",
    "Soldat de 3ᵉ classe",
    "Soldat de 2ᵉ classe",
    "Soldat de 1ʳᵉ classe",
    "Sous-Capitaine",
    "Capitaine",
    "Senior Capitaine",
    "Commandant",
    "Sous-Supérieur",
    "Supérieur Délégué",
    "Supérieur Général Délégué",
    "Supérieur Général",
    "Supérieur Suprême Spirituel",
]


def test_grades_dans_l_ordre():
    assert [g.label for g in Grade] == LIBELLES
    assert Grade.CAMARADE == 0
    assert Grade.CAPITAINE == 5
    assert Grade.SUPREME == 12


@pytest.mark.parametrize(
    "texte,attendu",
    [
        ("camarade", 0),
        ("capitaine", 5),
        ("Soldat de 3e classe", 1),
        ("soldat de 3ème classe", 1),
        ("3ᵉ classe", 1),
        ("Soldat de 1ere classe", 3),
        ("1re classe", 3),
        ("sous capitaine", 4),
        ("Sous-Capitaine", 4),
        ("SUPERIEUR SUPREME SPIRITUEL", 12),
        ("  senior   capitaine ", 6),
        ("Général", None),
        ("", None),
        (None, None),
    ],
)
def test_grade_depuis_texte(texte, attendu):
    assert grade_depuis_texte(texte) == attendu


def test_nom_complet_avec_grade():
    m = Membre(nom="koudakpo", prenoms="Marc Aurel", grade=5)
    assert m.nom_complet == "Capitaine Marc Aurel KOUDAKPO"


def test_nom_complet_camarade():
    assert Membre(nom="Koudakpo", prenoms="Marc Aurel", grade=0).nom_complet == (
        "Camarade Marc Aurel KOUDAKPO"
    )


def test_nom_complet_sans_grade():
    assert Membre(nom="Koudakpo", prenoms="Marc Aurel").nom_complet == "Marc Aurel KOUDAKPO"


def test_historique_ne_se_supprime_pas(monde):
    import datetime

    from apps.grades.models import HistoriqueGrade, ModeGrade

    h = HistoriqueGrade.objects.create(
        membre=monde["m1"], grade=1, date_effet=datetime.date(2020, 1, 1), mode=ModeGrade.TEST
    )
    with pytest.raises(PermissionDenied):
        h.delete()
