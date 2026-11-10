import pytest

from apps.comptes.models import Compte
from apps.lots.controle import creer_lot, remplacer_fichier
from apps.lots.lecture import FichierInvalide
from apps.lots.models import EtatLigne, Lot
from apps.membres.models import CompteurMatricule, Membre


def _l(nom="Hounkpè", prenoms="Jean-Marc", date="01/05/1990", npi="", paroisse="P1"):
    return [
        nom,
        prenoms,
        "M",
        date,
        "",
        "",
        npi,
        "0197000000",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        2015,
        paroisse,
        "",
    ]


def _creer(territoire, compte_technique, classeur, lignes):
    return creer_lot(region=territoire["HOULENOU"], fichier=classeur(lignes), par=compte_technique)


def test_meme_personne_deux_fois_dans_le_fichier(territoire, compte_technique, classeur):
    lot = _creer(
        territoire,
        compte_technique,
        classeur,
        [_l(), _l(nom="HOUNKPE", prenoms="jean marc"), _l(nom="Autre")],
    )
    l2, l3, l4 = lot.lignes.all()
    assert l2.etat == l3.etat == EtatLigne.DOUBLON
    assert "ligne 3" in l2.doublons and "ligne 2" in l3.doublons
    assert l4.etat == EtatLigne.CORRECTE


def test_doublon_par_npi_dans_le_fichier(territoire, compte_technique, classeur):
    lot = _creer(
        territoire,
        compte_technique,
        classeur,
        [_l(npi="1234567890"), _l(nom="Autre", npi="1234567890")],
    )
    assert {x.etat for x in lot.lignes.all()} == {EtatLigne.DOUBLON}


def test_doublon_avec_membre_existant(territoire, compte_technique, classeur, nouveau_membre):
    import datetime

    m = nouveau_membre(territoire["P2"], "Hounkpè", prenoms="Jean-Marc")
    m.date_naissance = datetime.date(1990, 5, 1)
    m.save()
    lot = _creer(territoire, compte_technique, classeur, [_l()])
    ligne = lot.lignes.get()
    assert ligne.etat == EtatLigne.DOUBLON and m.matricule in ligne.doublons


def test_creer_lot_ne_cree_aucun_membre(territoire, compte_technique, classeur):
    avant = (Membre.objects.count(), Compte.objects.count(), CompteurMatricule.objects.count())
    lot = _creer(territoire, compte_technique, classeur, [_l(), _l(nom="Bio")])
    assert lot.lignes.count() == 2 and lot.nom_fichier == "lot.xlsx" and lot.fichier
    assert (
        Membre.objects.count(),
        Compte.objects.count(),
        CompteurMatricule.objects.count(),
    ) == avant


def test_fichier_invalide_aucun_lot(territoire, compte_technique, classeur):
    with pytest.raises(FichierInvalide):
        _creer(
            territoire,
            compte_technique,
            lambda lignes: classeur(lignes, entetes_modifiees={0: "Nom"}),
            [_l()],
        )
    assert not Lot.objects.exists()


def test_doublon_garde_reste_garde(territoire, compte_technique, classeur):
    from apps.lots.controle import controler_lot

    lot = _creer(territoire, compte_technique, classeur, [_l(), _l(nom="HOUNKPE")])
    lot.lignes.update(etat=EtatLigne.GARDEE)
    controler_lot(lot)
    assert {x.etat for x in lot.lignes.all()} == {EtatLigne.GARDEE}


def test_remplacer_fichier(territoire, compte_technique, classeur):
    lot = _creer(territoire, compte_technique, classeur, [_l(), _l(nom="Bio")])
    remplacer_fichier(lot, classeur([_l(nom="Chabi")], nom="corrige.xlsx"), compte_technique)
    assert [x.brutes["Nom*"] for x in lot.lignes.all()] == ["Chabi"]
    assert lot.nom_fichier == "corrige.xlsx"
