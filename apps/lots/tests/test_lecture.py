import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.lots.colonnes import COLONNES
from apps.lots.controle import normaliser_ligne
from apps.lots.lecture import FichierInvalide, lire_classeur

LIGNE_OK = [
    "Hounkpè",
    "Jean-Marc",
    "M",
    "01/05/1990",
    "",
    "",
    "",
    "0197000000",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    2015,
    "P1",
    "",
]


def _brutes(**remplacements):
    b = dict(zip([c.entete for c in COLONNES], LIGNE_OK + ["", "", ""], strict=True))
    b.update(remplacements)
    return b


def test_lecture_ignore_lignes_vides(classeur):
    lignes = lire_classeur(classeur([LIGNE_OK, [None] * 18, LIGNE_OK, [None] * 18]))
    assert [n for n, _ in lignes] == [2, 4]
    assert lignes[0][1]["Nom*"] == "Hounkpè"


def test_fichier_non_excel():
    with pytest.raises(FichierInvalide, match="pas un classeur Excel"):
        lire_classeur(SimpleUploadedFile("x.xlsx", b"nom;prenoms\nA;B"))


def test_feuille_membres_absente(classeur):
    import io

    from openpyxl import load_workbook

    f = classeur([LIGNE_OK])
    wb = load_workbook(io.BytesIO(f.read()))
    wb["Membres"].title = "Feuil1"
    tampon = io.BytesIO()
    wb.save(tampon)
    with pytest.raises(FichierInvalide, match="feuille « Membres »"):
        lire_classeur(SimpleUploadedFile("x.xlsx", tampon.getvalue()))


def test_colonnes_deplacees(classeur):
    with pytest.raises(FichierInvalide, match="colonne B attendue « Prénoms\\* »"):
        lire_classeur(classeur([LIGNE_OK], entetes_modifiees={1: "Téléphone*"}))


def test_trop_de_lignes(classeur, monkeypatch):
    from apps.lots import lecture

    monkeypatch.setattr(lecture, "LIGNES_MAX", 2)
    with pytest.raises(FichierInvalide, match="2 lignes au plus"):
        lire_classeur(classeur([LIGNE_OK] * 3))


@pytest.mark.parametrize(
    "valeur,attendu",
    [
        (datetime.datetime(1990, 5, 1), "1990-05-01"),
        ("01/05/1990", "1990-05-01"),
        (" 1/5/1990 ", "1990-05-01"),
        ("1990", None),
        ("01-05-90", None),
        ("31/02/1990", None),
    ],
)
def test_dates(territoire, valeur, attendu):
    donnees, erreurs = normaliser_ligne(
        _brutes(**{"Date de naissance": valeur}), territoire["HOULENOU"]
    )
    if attendu:
        assert donnees["date_naissance"] == attendu and not erreurs
    else:
        assert "Date de naissance : date invalide, écrivez JJ/MM/AAAA" in erreurs


def test_paroisse_ecrite_autrement_et_autre_region(territoire):
    from apps.organisation.models import Paroisse

    p = Paroisse.objects.create(
        circuit=territoire["Ekpe A"], nom="Paroisse Saint Michel de TOKPOTA DAVO"
    )
    brutes = _brutes(**{"Paroisse d'intégration*": "  paroisse saint  michel de tokpota davo "})
    assert normaliser_ligne(brutes, territoire["HOULENOU"])[0]["paroisse_integration"] == p.pk
    erreurs = normaliser_ligne(
        _brutes(**{"Paroisse d'intégration*": "P4"}), territoire["HOULENOU"]
    )[1]
    assert "Paroisse d'intégration* : « P4 » n'existe pas dans la région HOULENOU" in erreurs


def test_paroisse_fermee_refusee(territoire):
    territoire["P1"].fermer()
    erreurs = normaliser_ligne(_brutes(), territoire["HOULENOU"])[1]
    assert any("« P1 » n'existe pas" in e for e in erreurs)


def test_categorie_et_sexe(territoire):
    d, e = normaliser_ligne(_brutes(), territoire["HOULENOU"])
    assert d["categorie"] == "actif" and d["sexe"] == "M" and not e
    d, e = normaliser_ligne(
        _brutes(**{"Catégorie": "Membre d'honneur", "Sexe*": "f"}), territoire["HOULENOU"]
    )
    assert d["categorie"] == "honneur" and d["sexe"] == "F"
    e = normaliser_ligne(_brutes(**{"Catégorie": "Ami"}), territoire["HOULENOU"])[1]
    assert any(x.startswith("Catégorie :") for x in e)


def test_annee_texte_et_nombre(territoire):
    assert (
        normaliser_ligne(_brutes(**{"Année d'intégration*": "2015"}), territoire["HOULENOU"])[0][
            "annee_integration"
        ]
        == 2015
    )
    e = normaliser_ligne(_brutes(**{"Année d'intégration*": "deux mille"}), territoire["HOULENOU"])[
        1
    ]
    assert any(x.startswith("Année d'intégration* :") for x in e)


def test_telephone_nombre_excel(territoire):
    # Un nombre a pu perdre son 0 initial dans Excel : on demande de l'écrire comme du texte.
    erreurs = normaliser_ligne(_brutes(**{"Téléphone*": 197000000}), territoire["HOULENOU"])[1]
    assert any("0 initial" in e for e in erreurs)
