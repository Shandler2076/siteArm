"""Grade à l'enregistrement : formulaire du BN et lots Excel (régularisation, art. 83)."""

import datetime

from apps.grades.models import ModeGrade
from apps.membres.models import Membre
from apps.membres.services import enregistrer_membre

D = datetime.date


def _donnees():
    return {
        "nom": "Koudakpo",
        "prenoms": "Marc Aurel",
        "sexe": "M",
        "telephone": "0197000000",
        "categorie": "actif",
        "date_naissance": D(1990, 5, 1),
    }


def test_enregistrement_camarade_par_defaut(territoire, compte_technique):
    m = enregistrer_membre(
        donnees=_donnees(),
        paroisse_integration=territoire["P1"],
        annee_integration=2015,
        par=compte_technique,
    ).membre
    m.refresh_from_db()
    assert m.grade == 0 and m.date_grade == D(2015, 1, 1)
    h = m.grades.get()
    assert h.mode == ModeGrade.ENTREE
    assert m.compte.nom_affiche == "Camarade Marc Aurel KOUDAKPO"


def test_enregistrement_regularisation_service(territoire, compte_technique):
    m = enregistrer_membre(
        donnees=_donnees(),
        paroisse_integration=territoire["P1"],
        annee_integration=2010,
        par=compte_technique,
        grade=5,
        date_grade=D(2018, 3, 15),
        regularisation=True,
    ).membre
    assert m.grades.get().mode == ModeGrade.REGULARISATION
    assert m.compte.nom_affiche == "Capitaine Marc Aurel KOUDAKPO"


URL = "/membres/bn/enregistrer/"


def _post(client, paroisse, **extra):
    d = {
        "nom": "Koudakpo",
        "prenoms": "Marc Aurel",
        "sexe": "M",
        "telephone": "0197000000",
        "date_naissance": "1990-05-01",
        "annee_integration": "2010",
        "paroisse_integration": paroisse.pk,
        "categorie": "actif",
        "grade": "0",
    }
    d.update(extra)
    return client.post(URL, d)


def test_formulaire_regularisation_capitaine(client_technique, territoire):
    r = _post(client_technique, territoire["P1"], grade="5", date_grade="2018-03-15")
    assert r.status_code == 302
    m = Membre.objects.get()
    assert (m.grade, m.date_grade) == (5, D(2018, 3, 15))
    assert m.grades.get().mode == ModeGrade.REGULARISATION
    assert m.compte.nom_affiche.startswith("Capitaine")


def test_formulaire_camarade_par_defaut(client_technique, territoire):
    r = client_technique.get(URL)
    assert 'value="0" selected' in r.content.decode() or "Camarade" in r.content.decode()
    _post(client_technique, territoire["P1"])
    assert Membre.objects.get().grade == 0


def test_date_grade_avant_naissance_refusee(client_technique, territoire):
    r = _post(client_technique, territoire["P1"], grade="5", date_grade="1980-01-01")
    assert r.status_code == 200 and not Membre.objects.exists()
    assert "date de naissance" in r.content.decode()


def test_date_grade_avant_integration_refusee(client_technique, territoire):
    r = _post(client_technique, territoire["P1"], grade="5", date_grade="2009-12-31")
    assert r.status_code == 200 and not Membre.objects.exists()
    assert "intégration" in r.content.decode()


# --- Lots -----------------------------------------------------------------------------------


def _l(nom, grade="", date_grade=""):
    return [
        nom,
        "Test",
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
        grade,
        date_grade,
    ]


def _lot(territoire, compte_technique, classeur, lignes, **kw):
    from apps.lots.controle import creer_lot

    return creer_lot(
        region=territoire["HOULENOU"], par=compte_technique, fichier=classeur(lignes, **kw)
    )


def test_lot_grade_libre_reconnu(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo", "capitaine", "15/03/2018")])
    ligne = lot.lignes.get()
    assert ligne.erreurs == []
    assert ligne.donnees["grade"] == 5 and ligne.donnees["date_grade"] == "2018-03-15"


def test_lot_grade_inconnu_erreur_de_ligne(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo", "Général")])
    assert any(e.startswith("Grade : grade inconnu « Général »") for e in lot.lignes.get().erreurs)


def test_lot_date_grade_sans_grade(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo", "", "15/03/2018")])
    assert any(e.startswith("Date du grade :") for e in lot.lignes.get().erreurs)


def test_lot_date_grade_avant_integration(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo", "Capitaine", "01/01/2010")])
    assert any("intégration" in e for e in lot.lignes.get().erreurs)


def test_lot_sans_colonne_grade_camarade(territoire, compte_technique, classeur):
    """Un fichier fait avec l'ancien modèle (sans les colonnes du grade) reste accepté."""
    from apps.lots.colonnes import COLONNES

    anciennes = [c.entete for c in COLONNES if c.champ not in ("grade", "date_grade")]
    lignes = [_l("Agbo")[: len(anciennes)]]
    lot = _lot(
        territoire,
        compte_technique,
        classeur,
        lignes,
        entetes_modifiees={len(anciennes): None, len(anciennes) + 1: None},
    )
    ligne = lot.lignes.get()
    assert ligne.erreurs == [] and ligne.donnees["grade"] is None


def test_lot_valide_cree_historique(territoire, compte_technique, classeur):
    from apps.lots.generation import valider_lot

    lot = _lot(
        territoire,
        compte_technique,
        classeur,
        [_l("Agbo", "Capitaine", "15/03/2018"), _l("Bio")],
    )
    valider_lot(lot, compte_technique)
    agbo = Membre.objects.get(nom="Agbo")
    bio = Membre.objects.get(nom="Bio")
    assert (agbo.grade, agbo.grades.get().mode) == (5, ModeGrade.REGULARISATION)
    assert (bio.grade, bio.grades.get().mode) == (0, ModeGrade.ENTREE)
