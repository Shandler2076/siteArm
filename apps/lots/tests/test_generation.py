import datetime
import io

import pytest

from apps.lots.controle import creer_lot
from apps.lots.generation import GenerationEchouee, valider_lot
from apps.lots.models import EtatLigne, EtatLot
from apps.membres.models import CompteurMatricule, Membre
from apps.notifications.models import Notification


def _l(nom, prenoms="Test", annee=2015):
    return [
        nom,
        prenoms,
        "M",
        "",
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
        annee,
        "P1",
        "",
    ]


@pytest.fixture
def lot_pret(territoire, compte_technique, classeur):
    return creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([_l("Agbo"), _l("Bio")]),
    )


@pytest.fixture
def secretaire_p1(territoire, nouveau_membre, donner_mandat):
    m = nouveau_membre(territoire["P1"], "Secretaire")
    donner_mandat(m, "Secrétaire paroissial", territoire["P1"], debut=datetime.date(2025, 1, 1))
    return m


def test_generation_complete(lot_pret, compte_technique):
    membres = valider_lot(lot_pret, compte_technique)
    assert [m.matricule for m in membres] == ["2015-03AS-0001", "2015-03AS-0002"]
    lot_pret.refresh_from_db()
    assert lot_pret.etat == EtatLot.VALIDE and lot_pret.valide_par == compte_technique
    assert [x.membre.nom for x in lot_pret.lignes.all()] == ["Agbo", "Bio"]
    assert membres[0].affectation_actuelle.date_debut == datetime.date(2015, 1, 1)


def test_lignes_ecartees_non_creees(lot_pret, compte_technique):
    lot_pret.lignes.filter(numero=3).update(etat=EtatLigne.ECARTEE)
    assert [m.nom for m in valider_lot(lot_pret, compte_technique)] == ["Agbo"]


def test_tout_ou_rien(lot_pret, compte_technique):
    CompteurMatricule.objects.create(annee=2015, region=lot_pret.region, dernier_numero=9998)
    with pytest.raises(GenerationEchouee, match="Ligne 3 .*Aucun membre n'a été créé"):
        valider_lot(lot_pret, compte_technique)
    assert Membre.objects.filter(nom__in=["Agbo", "Bio"]).count() == 0
    assert CompteurMatricule.objects.get(annee=2015).dernier_numero == 9998
    lot_pret.refresh_from_db()
    assert lot_pret.etat == EtatLot.BROUILLON


def test_une_notification_par_bureau(
    lot_pret, secretaire_p1, compte_technique, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        valider_lot(lot_pret, compte_technique)
    messages = list(
        Notification.objects.filter(destinataire=secretaire_p1.compte).values_list(
            "message", flat=True
        )
    )
    assert messages == [f"2 nouveaux membres dans votre périmètre (lot n° {lot_pret.pk})."]


def test_lot_non_validable_refuse(territoire, compte_technique, classeur):
    ligne_fausse = _l("Agbo")
    ligne_fausse[7] = "abc"  # téléphone invalide
    lot = creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([ligne_fausse, _l("Bio")]),
    )
    with pytest.raises(GenerationEchouee, match="ne peut pas être validé"):
        valider_lot(lot, compte_technique)


def test_double_validation_refusee(lot_pret, compte_technique):
    valider_lot(lot_pret, compte_technique)
    with pytest.raises(GenerationEchouee):
        valider_lot(lot_pret, compte_technique)
    assert Membre.objects.filter(nom__in=["Agbo", "Bio"]).count() == 2


def test_page_confirmation(client_technique, lot_pret):
    html = client_technique.get(f"/lots/{lot_pret.pk}/confirmer/").content.decode()
    assert "2 membres vont être créés pour la région 03" in html and "2015 : 2" in html
    r = client_technique.post(f"/lots/{lot_pret.pk}/confirmer/", {})
    assert "Cochez la case pour confirmer." in r.content.decode()
    assert not Membre.objects.filter(nom="Agbo").exists()
    r = client_technique.post(f"/lots/{lot_pret.pk}/confirmer/", {"confirme": "on"})
    assert r.status_code == 302 and r.url == f"/lots/{lot_pret.pk}/resultat/"
    html = client_technique.get(r.url).content.decode()
    assert "2015-03AS-0001" in html and "AGBO" in html


def test_echec_affiche_sur_le_controle(client_technique, lot_pret):
    CompteurMatricule.objects.create(annee=2015, region=lot_pret.region, dernier_numero=9999)
    r = client_technique.post(f"/lots/{lot_pret.pk}/confirmer/", {"confirme": "on"}, follow=True)
    assert "Aucun membre n&#x27;a été créé" in r.content.decode()


def test_resultat_lot_brouillon_404(client_technique, lot_pret):
    assert client_technique.get(f"/lots/{lot_pret.pk}/resultat/").status_code == 404


def test_enregistrement_individuel_notifie_toujours(
    territoire, secretaire_p1, nouveau_membre, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        nouveau_membre(territoire["P1"], "Seul")
    assert Notification.objects.filter(destinataire=secretaire_p1.compte).count() == 1


def test_lot_colonne_paroisse_actuelle(territoire, compte_technique, classeur):
    """Colonne facultative « Paroisse actuelle » (paroisse de la même région)."""
    ligne_actuelle = _l("Agbo") + ["", "", "P3"]  # Grade, Date du grade, Paroisse actuelle
    ligne_inconnue = _l("Bio") + ["", "", "Inconnue"]
    lot = creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([ligne_actuelle, _l("Chabi")]),
    )
    valider_lot(lot, par=compte_technique)
    agbo = Membre.objects.get(nom__iexact="Agbo")
    assert agbo.paroisse_integration == territoire["P1"]
    assert agbo.affectation_actuelle.paroisse == territoire["P3"]
    assert Membre.objects.get(nom__iexact="Chabi").affectations.count() == 1
    lot2 = creer_lot(
        region=territoire["HOULENOU"],
        par=compte_technique,
        fichier=classeur([ligne_inconnue], nom="lot2.xlsx"),
    )
    ligne = lot2.lignes.get()
    assert ligne.etat == EtatLigne.ERREUR
    assert any("Paroisse actuelle" in e for e in ligne.erreurs)


def test_modele_excel_a_la_colonne_paroisse_actuelle(territoire):
    from openpyxl import load_workbook

    from apps.lots.modele_excel import modele_pour_region

    wb = load_workbook(io.BytesIO(modele_pour_region(territoire["HOULENOU"])))
    entetes = [c.value for c in wb["Membres"][1]]
    assert entetes[-1] == "Paroisse actuelle"
