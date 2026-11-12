import pytest

from apps.lots.colonnes import COLONNES
from apps.lots.models import EtatLigne, LigneLot, Lot


@pytest.fixture
def lot(territoire, compte_technique):
    return Lot.objects.create(
        region=territoire["HOULENOU"], nom_fichier="x.xlsx", cree_par=compte_technique
    )


def _ligne(lot, numero, etat):
    return LigneLot.objects.create(lot=lot, numero=numero, etat=etat, brutes={}, donnees={})


def test_lot_validable(lot):
    _ligne(lot, 2, EtatLigne.CORRECTE)
    erreur = _ligne(lot, 3, EtatLigne.ERREUR)
    assert not lot.validable
    erreur.etat = EtatLigne.ECARTEE
    erreur.save()
    assert lot.validable
    lot.lignes.update(etat=EtatLigne.ECARTEE)
    assert not lot.validable


def test_doublon_non_tranche_bloque(lot):
    _ligne(lot, 2, EtatLigne.DOUBLON)
    assert not lot.validable
    lot.lignes.update(etat=EtatLigne.GARDEE)
    assert lot.validable


def test_nb_par_etat(lot):
    _ligne(lot, 2, EtatLigne.CORRECTE)
    _ligne(lot, 3, EtatLigne.CORRECTE)
    _ligne(lot, 4, EtatLigne.ERREUR)
    assert lot.nb_par_etat == {"correcte": 2, "erreur": 1}


def test_colonnes_ordre_et_obligatoires():
    assert len(COLONNES) == 20
    assert [c.entete for c in COLONNES if c.obligatoire] == [
        "Nom*",
        "Prénoms*",
        "Sexe*",
        "Téléphone*",
        "Année d'intégration*",
        "Paroisse d'intégration*",
    ]
    assert COLONNES[0].champ == "nom" and COLONNES[17].champ == "categorie"
    # Colonnes du grade ajoutées à la fin : les anciens fichiers restent acceptés.
    assert [(c.champ, c.entete_facultative) for c in COLONNES[18:]] == [
        ("grade", True),
        ("date_grade", True),
    ]


def test_fichier_lot_prive(lot):
    from apps.membres.stockage import stockage_prive

    assert lot.fichier.storage is stockage_prive
    assert str(lot) == f"Lot n° {lot.pk} — HOULENOU"
