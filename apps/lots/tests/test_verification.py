import pytest

from apps.lots.colonnes import COLONNES
from apps.lots.controle import verifier_ligne
from apps.lots.models import EtatLigne, LigneLot, Lot

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


@pytest.fixture
def lot(territoire, compte_technique):
    return Lot.objects.create(region=territoire["HOULENOU"], cree_par=compte_technique)


def _ligne(lot, **remplacements):
    brutes = dict(zip([c.entete for c in COLONNES], LIGNE_OK + ["", "", ""], strict=True))
    brutes.update(remplacements)
    n = lot.lignes.count() + 2
    return LigneLot.objects.create(lot=lot, numero=n, brutes=brutes)


def test_ligne_correcte(lot):
    ligne = _ligne(lot)
    verifier_ligne(ligne)
    assert ligne.etat == EtatLigne.CORRECTE and ligne.erreurs == []
    assert ligne.donnees["nom"] == "Hounkpè" and ligne.donnees["annee_integration"] == 2015


@pytest.mark.parametrize(
    "colonne,valeur,message",
    [
        ("Téléphone*", "abc", "Téléphone* : Numéro de téléphone invalide"),
        ("NPI", "12", "NPI : Le NPI comporte 10 chiffres."),
        (
            "Année d'intégration*",
            1800,
            "Année d'intégration* : L'année d'intégration doit être entre 1900",
        ),
        ("Nom*", "", "Nom* : Ce champ ne peut pas être vide."),
    ],
)
def test_erreurs_du_modele_reutilisees(lot, colonne, valeur, message):
    ligne = _ligne(lot, **{colonne: valeur})
    verifier_ligne(ligne)
    assert ligne.etat == EtatLigne.ERREUR
    assert any(e.startswith(message) for e in ligne.erreurs), ligne.erreurs


def test_npi_deja_utilise(lot, territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Existant")
    m.npi = "1234567890"
    m.save()
    ligne = _ligne(lot, NPI="1234567890")
    verifier_ligne(ligne)
    assert "Ce NPI est déjà utilisé par un autre membre." in " ".join(ligne.erreurs)


def test_ligne_ecartee_non_touchee(lot):
    ligne = _ligne(lot, **{"Téléphone*": "abc"})
    ligne.etat = EtatLigne.ECARTEE
    verifier_ligne(ligne)
    assert ligne.etat == EtatLigne.ECARTEE and ligne.erreurs == []
