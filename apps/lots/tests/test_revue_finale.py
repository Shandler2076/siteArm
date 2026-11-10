"""Corrections issues de la relecture finale de l'étape 4."""

import datetime
import io

import pytest
from openpyxl import load_workbook

from apps.lots.colonnes import COLONNES
from apps.lots.controle import controler_lot, creer_lot, remplacer_fichier
from apps.lots.generation import GenerationEchouee, valider_lot
from apps.lots.modele_excel import modele_pour_region
from apps.lots.models import EtatLigne, EtatLot, Lot
from apps.membres.models import Membre


def _l(nom, date="", tel="0197000000", npi="", paroisse="P1"):
    return [
        nom,
        "Test",
        "M",
        date,
        "",
        "",
        npi,
        tel,
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


def _lot(territoire, compte, classeur, lignes):
    return creer_lot(region=territoire["HOULENOU"], fichier=classeur(lignes), par=compte)


# C1 — une vraie cellule date Excel passe par la base et reste acceptée
def test_vraie_date_excel_acceptee(territoire, compte_technique, classeur, client_technique):
    lot = _lot(
        territoire, compte_technique, classeur, [_l("Agbo", date=datetime.datetime(1985, 3, 12))]
    )
    ligne = lot.lignes.get()
    assert ligne.etat == EtatLigne.CORRECTE, ligne.erreurs
    assert ligne.donnees["date_naissance"] == "1985-03-12"
    html = client_technique.get(f"/lots/{lot.pk}/").content.decode()
    assert "12/03/1985" in html and "1985-03-12T00:00:00" not in html


# C2 — doublons revérifiés à la validation : pas de création en double
def test_meme_fichier_depose_deux_fois(territoire, compte_technique, classeur):
    a = _lot(territoire, compte_technique, classeur, [_l("Agbo"), _l("Bio")])
    b = _lot(territoire, compte_technique, classeur, [_l("Agbo"), _l("Bio")])
    valider_lot(a, compte_technique)
    with pytest.raises(GenerationEchouee, match="revérifiez"):
        valider_lot(b, compte_technique)
    assert Membre.objects.filter(nom="Agbo").count() == 1
    b.refresh_from_db()
    assert b.etat == EtatLot.BROUILLON
    assert {x.etat for x in b.lignes.all()} == {EtatLigne.DOUBLON}


def test_paroisse_fermee_entre_controle_et_validation(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo")])
    territoire["P1"].fermer()
    with pytest.raises(GenerationEchouee):
        valider_lot(lot, compte_technique)
    assert not Membre.objects.filter(nom="Agbo").exists()


# I3 — performances : nombre de requêtes borné, pas de hachage inutile
def test_controle_nombre_de_requetes_borne(
    territoire, compte_technique, classeur, django_assert_max_num_queries
):
    lot = _lot(
        territoire,
        compte_technique,
        classeur,
        [_l(f"Nom{i}", npi=f"{1000000000 + i}") for i in range(40)],
    )
    with django_assert_max_num_queries(120):
        controler_lot(lot)


def test_validation_sans_hachage_de_mot_de_passe(
    territoire, compte_technique, classeur, monkeypatch
):
    from django.contrib.auth import base_user

    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo"), _l("Bio")])
    appels = []
    vrai = base_user.make_password
    monkeypatch.setattr(
        base_user, "make_password", lambda *a, **k: appels.append(a[0]) or vrai(*a, **k)
    )
    membres = valider_lot(lot, compte_technique)
    assert all(not m.compte.has_usable_password() for m in membres)
    assert [x for x in appels if x is not None] == []


def test_fiches_par_tranches_de_100(client_technique, territoire, compte_technique, classeur):
    lot = _lot(
        territoire,
        compte_technique,
        classeur,
        [_l(f"Nom{i}", npi=f"{1000000000 + i}") for i in range(3)],
    )
    valider_lot(lot, compte_technique)
    html = client_technique.get(f"/lots/{lot.pk}/resultat/").content.decode()
    assert "Fiches 1 à 3" in html
    r = client_technique.post(f"/lots/{lot.pk}/fiches.pdf", {"debut": "2", "fin": "3"})
    from pypdf import PdfReader

    assert len(PdfReader(io.BytesIO(r.content)).pages) == 2


def test_procfile_delai_suffisant():
    from pathlib import Path

    procfile = (Path(__file__).resolve().parents[3] / "Procfile").read_text()
    assert "--timeout 120" in procfile


# I4 — un lot validé ne peut pas être modifié, même avec un objet périmé
def test_remplacer_fichier_sur_objet_perime_refuse(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo")])
    perime = Lot.objects.get(pk=lot.pk)
    valider_lot(lot, compte_technique)
    with pytest.raises(ValueError, match="validé"):
        remplacer_fichier(perime, classeur([_l("Bio")]), compte_technique)
    lot.refresh_from_db()
    assert lot.etat == EtatLot.VALIDE and lot.lignes.get().membre is not None


def test_controle_d_un_lot_valide_ne_touche_rien(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo")])
    valider_lot(lot, compte_technique)
    controler_lot(lot)
    ligne = lot.lignes.get()
    assert ligne.etat == EtatLigne.CORRECTE and ligne.membre is not None


# I5 — téléphones et NPI : format texte dans le modèle, nombres refusés clairement
def test_modele_colonnes_texte(territoire):
    ws = load_workbook(io.BytesIO(modele_pour_region(territoire["HOULENOU"])))["Membres"]
    for champ in ["telephone", "whatsapp", "urgence_telephone", "npi"]:
        lettre = chr(ord("A") + [c.champ for c in COLONNES].index(champ))
        assert ws[f"{lettre}2"].number_format == "@", champ


def test_telephone_saisi_comme_nombre_refuse(territoire, compte_technique, classeur):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo", tel=197000000)])
    ligne = lot.lignes.get()
    assert ligne.etat == EtatLigne.ERREUR
    assert any("0 initial" in e for e in ligne.erreurs)


# I6 — le fichier d'origine (et les précédents) restent consultables
def test_telechargement_du_fichier_d_origine(
    client_technique, client, territoire, compte_technique, classeur, nouveau_membre
):
    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo")])
    remplacer_fichier(lot, classeur([_l("Bio")], nom="corrige.xlsx"), compte_technique)
    r = client_technique.get(f"/lots/{lot.pk}/fichiers/0/")
    assert r.status_code == 200 and "no-store" in r["Cache-Control"]
    premier = load_workbook(io.BytesIO(b"".join(r.streaming_content)))["Membres"]
    assert premier["A2"].value == "Agbo"
    r = client_technique.get(f"/lots/{lot.pk}/fichiers/1/")
    assert load_workbook(io.BytesIO(b"".join(r.streaming_content)))["Membres"]["A2"].value == "Bio"
    html = client_technique.get(f"/lots/{lot.pk}/").content.decode()
    assert f"/lots/{lot.pk}/fichiers/0/" in html and "corrige.xlsx" in html
    client.force_login(nouveau_membre(territoire["P2"], "X").compte)
    assert client.get(f"/lots/{lot.pk}/fichiers/0/").status_code == 403


# Relevé à la hausse — l'impression ne réinitialise pas les membres déjà connectés
def test_fiches_ne_reinitialisent_pas_les_membres_deja_connectes(
    territoire, compte_technique, classeur, client_technique
):
    from django.utils import timezone

    lot = _lot(territoire, compte_technique, classeur, [_l("Agbo"), _l("Bio")])
    agbo, bio = valider_lot(lot, compte_technique)
    agbo.compte.set_password("MonPropreMot!2026")
    agbo.compte.last_login = timezone.now()
    agbo.compte.save()
    client_technique.post(f"/lots/{lot.pk}/fiches.pdf")
    agbo.compte.refresh_from_db()
    bio.compte.refresh_from_db()
    assert agbo.compte.check_password("MonPropreMot!2026")
    assert bio.compte.has_usable_password()


# Relevé à la hausse — le tableau montre les valeurs telles que le site les a comprises
def test_tableau_valeurs_comprises(territoire, compte_technique, classeur, client_technique):
    from apps.organisation.models import Paroisse

    Paroisse.objects.create(circuit=territoire["Ekpe A"], nom="Paroisse Saint Michel de DAVO")
    lot = _lot(
        territoire,
        compte_technique,
        classeur,
        [_l("Agbo", paroisse="paroisse  saint michel de davo")],
    )
    html = client_technique.get(f"/lots/{lot.pk}/").content.decode()
    assert "Paroisse Saint Michel de DAVO" in html
