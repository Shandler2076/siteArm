import datetime

import pytest
from django.contrib.auth.password_validation import validate_password

from apps.comptes.models import Compte
from apps.membres.models import CompteurMatricule, Membre
from apps.membres.services import (
    CapaciteMatriculeAtteinte,
    cle_nom,
    doublons_possibles,
    enregistrer_membre,
    generer_mot_de_passe_provisoire,
)


@pytest.fixture
def contexte(db):
    from apps.organisation.models import Circuit, Paroisse, Region

    r = Region.objects.create(code="03", nom="HOULENOU")
    p = Paroisse.objects.create(circuit=Circuit.objects.create(region=r, nom="Ekpe A"), nom="P1")
    bn = Compte.objects.create_superuser("tech", "MotDePasse!2026")
    return p, bn


DONNEES = dict(
    nom="Hounkpè",
    prenoms="Jean-Marc",
    sexe="M",
    telephone="0197000000",
    date_naissance=datetime.date(1990, 5, 1),
    categorie="honneur",
)


def _enregistrer(p, bn, annee=2015, **extra):
    return enregistrer_membre(
        donnees={**DONNEES, **extra}, paroisse_integration=p, annee_integration=annee, par=bn
    )


def test_enregistrement_complet(contexte):
    p, bn = contexte
    res = _enregistrer(p, bn)
    m = res.membre
    assert m.matricule == "2015-03AS-0001" and m.region_integration.code == "03"
    assert m.categorie == "honneur" and m.statut == "actif" and m.enregistre_par == bn
    assert m.compte.identifiant == "2015-03AS-0001"
    assert m.compte.nom_affiche == "Camarade Jean-Marc HOUNKPÈ"
    assert m.compte.doit_changer_mot_de_passe and m.compte.check_password(res.mot_de_passe)
    a = m.affectation_actuelle
    assert a.paroisse == p and a.circuit_a_date == p.circuit and a.region_a_date.code == "03"
    assert a.date_debut == datetime.date(2015, 1, 1) and a.motif == "Intégration"


def test_echec_n_avance_pas_le_compteur(contexte):
    p, bn = contexte
    with pytest.raises(Exception):  # noqa: B017
        _enregistrer(p, bn, sexe="X_INVALIDE_TROP_LONG")
    assert not CompteurMatricule.objects.filter(dernier_numero__gt=0).exists()
    assert not Compte.objects.exclude(identifiant="TECH").exists()


def test_capacite_atteinte_rien_n_est_cree(contexte):
    p, bn = contexte
    CompteurMatricule.objects.create(annee=2015, region=p.region, dernier_numero=9999)
    with pytest.raises(CapaciteMatriculeAtteinte):
        _enregistrer(p, bn)
    assert Membre.objects.count() == 0
    assert not Compte.objects.exclude(identifiant="TECH").exists()


def test_cle_nom():
    assert cle_nom("  Hounkpè  Jean-Marc ") == cle_nom("HOUNKPE jean marc") == "HOUNKPE JEAN MARC"


def test_doublon_ecrit_autrement(contexte):
    p, bn = contexte
    _enregistrer(p, bn)
    assert (
        doublons_possibles(
            nom="HOUNKPE", prenoms="jean  marc", date_naissance=datetime.date(1990, 5, 1)
        ).count()
        == 1
    )
    assert (
        doublons_possibles(
            nom="HOUNKPE", prenoms="Paul", date_naissance=datetime.date(1990, 5, 1)
        ).count()
        == 0
    )


def test_doublon_sans_date_de_naissance(contexte):
    p, bn = contexte
    _enregistrer(p, bn, date_naissance=None)
    assert doublons_possibles(nom="hounkpe", prenoms="JEAN-MARC", date_naissance=None).count() == 1


def test_doublon_par_npi(contexte):
    p, bn = contexte
    _enregistrer(p, bn, npi="1234567890")
    assert (
        doublons_possibles(
            nom="Autre", prenoms="Nom", date_naissance=None, npi="1234567890"
        ).count()
        == 1
    )


def test_mot_de_passe_provisoire_valide():
    for _ in range(50):
        mdp = generer_mot_de_passe_provisoire()
        assert len(mdp) == 10 and not set(mdp) & set("0O1lI")
        validate_password(mdp)
