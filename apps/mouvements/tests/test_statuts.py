from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.mouvements.models import Mutation
from apps.mouvements.statuts import ajouter_mois, changer_categorie, changer_statut, clore_mandats


def test_deces_desactive_compte_et_clot_mandats(monde):
    sec = monde["sec_p1"]
    h = changer_statut(
        sec, "decede", par=None, date_effet=date(2026, 11, 1), motif="Décès confirmé"
    )
    sec.refresh_from_db()
    sec.compte.refresh_from_db()
    assert sec.statut == "decede" and not sec.compte.is_active and sec.matricule
    assert h.libelle == "Statut : Actif → Décédé" and h.ancien == "actif"
    assert h.date_effet == date(2026, 11, 1) and h.motif == "Décès confirmé"
    assert not sec.mandats.en_cours(date(2026, 11, 2)).exists()
    assert list(sec.historique.all()) == [h]


def test_retour_actif_reactive_compte(monde):
    m1 = monde["m1"]
    changer_statut(m1, "demissionnaire", par=None, date_effet=date(2026, 1, 1), motif="Démission")
    m1.compte.refresh_from_db()
    assert not m1.compte.is_active
    changer_statut(m1, "actif", par=None, date_effet=date(2026, 9, 1), motif="Réhabilitation")
    m1.compte.refresh_from_db()
    assert m1.compte.is_active and m1.statut == "actif"


def test_sanctionne_garde_le_compte(monde):
    m1 = monde["m1"]
    changer_statut(m1, "sanctionne", par=None, date_effet=date(2026, 1, 1), motif="Sanction")
    m1.compte.refresh_from_db()
    assert m1.compte.is_active


def test_changer_categorie_historique(monde, compte_technique):
    m1 = monde["m1"]
    h = changer_categorie(
        m1, "honneur", par=compte_technique, date_effet=date(2026, 11, 11), motif="Validé par le BN"
    )
    m1.refresh_from_db()
    assert m1.categorie == "honneur" and h.par == compte_technique
    assert h.libelle == "Catégorie : Membre actif → Membre d'honneur"


def test_clore_mandats_selon_unites(monde):
    chef, sec = monde["chef"], monde["sec_p1"]
    jour = date(2026, 11, 11)
    assert clore_mandats(chef, jour, {monde["P2"]}) == []
    assert chef.mandats.en_cours(jour).exists()
    (clos,) = clore_mandats(sec, jour, {monde["P1"]})
    assert clos.date_fin == jour and not sec.mandats.en_cours(jour).exists()


def test_clore_mandat_futur(monde, donner_mandat):
    m1 = monde["m1"]
    futur = donner_mandat(m1, "Secrétaire paroissial", monde["P1"], debut=date(2027, 1, 1))
    clore_mandats(m1, date(2026, 11, 11))
    futur.refresh_from_db()
    assert futur.date_fin == date(2027, 1, 1)
    assert not m1.mandats.en_cours(date(2027, 6, 1)).exists()


@pytest.mark.parametrize(
    "jour, mois, attendu",
    [
        (date(2026, 8, 31), 6, date(2027, 2, 28)),
        (date(2027, 8, 31), 6, date(2028, 2, 29)),
        (date(2026, 1, 15), 6, date(2026, 7, 15)),
        (date(2026, 7, 31), 6, date(2027, 1, 31)),
    ],
)
def test_ajouter_mois(jour, mois, attendu):
    assert ajouter_mois(jour, mois) == attendu


def test_une_seule_mutation_en_cours(monde, compte_technique):
    m1 = monde["m1"]
    kw = dict(
        membre=m1,
        paroisse_depart=monde["P1"],
        paroisse_arrivee=monde["P4"],
        demandee_par=compte_technique,
    )
    Mutation.objects.create(**kw)
    with pytest.raises(IntegrityError), transaction.atomic():
        Mutation.objects.create(**kw, etat="bn")
    Mutation.objects.create(**kw, etat="refusee")
