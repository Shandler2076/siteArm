import datetime

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.cotisations.models import EtatVersement, MoisCotise, Tarif, tarif_du
from apps.cotisations.regles import mois_dus, situation, situations
from apps.cotisations.tests.conftest import enregistre_le
from apps.membres.models import Membre
from apps.mouvements.models import HistoriqueMembre, TypeHistorique

D = datetime.date


def M(annee, mois):
    return D(annee, mois, 1)


def test_rien_du_sans_mois_de_depart(monde):
    assert mois_dus(monde["m1"], D(2026, 11, 12)) == []


def test_mois_dus_depuis_depart_ou_enregistrement(monde, depart):
    ancien = enregistre_le(monde["m1"], D(2025, 6, 3))
    recent = enregistre_le(monde["m2"], D(2026, 9, 20))
    assert mois_dus(ancien, D(2026, 3, 31)) == [M(2026, 1), M(2026, 2), M(2026, 3)]
    assert mois_dus(recent, D(2026, 11, 12)) == [M(2026, 9), M(2026, 10), M(2026, 11)]


def test_pas_du_apres_deces_et_de_nouveau_apres_rehabilitation(monde, depart):
    m = enregistre_le(monde["m1"], D(2025, 1, 1))
    for date_effet, ancien, nouveau in [
        (D(2026, 3, 15), "actif", "exclu"),
        (D(2026, 6, 10), "exclu", "actif"),
    ]:
        HistoriqueMembre.objects.create(
            membre=m,
            type=TypeHistorique.STATUT,
            ancien=ancien,
            nouveau=nouveau,
            date_effet=date_effet,
            motif="Test",
        )
    dus = mois_dus(m, D(2026, 8, 31))
    assert dus == [M(2026, 1), M(2026, 2), M(2026, 3), M(2026, 7), M(2026, 8)]


def test_membre_non_actif_sans_historique(monde, depart):
    m = enregistre_le(monde["m1"], D(2025, 1, 1))
    Membre.objects.filter(pk=m.pk).update(statut="decede")
    m.refresh_from_db()
    assert mois_dus(m, D(2026, 3, 31)) == []
    Membre.objects.filter(pk=m.pk).update(statut="sanctionne")
    m.refresh_from_db()
    assert len(mois_dus(m, D(2026, 3, 31))) == 3  # un sanctionné doit ses cotisations


def test_a_jour_et_retard(monde, depart, payer):
    m = enregistre_le(monde["m1"], D(2025, 1, 1))
    payer(m, [M(2026, 1), M(2026, 2)])
    s = situation(m, M(2026, 3))
    assert (s.retard, s.reste_du, s.a_jour) == (1, 100, False)
    assert s.total_annee == 200 and s.total_depuis_debut == 200
    payer(m, [M(2026, 3), M(2026, 4)])  # avril payé d'avance
    s = situation(m, M(2026, 3))
    assert s.a_jour and s.retard == 0 and M(2026, 4) in s.payes


def test_en_attente_ne_compte_pas(monde, depart, payer):
    m = enregistre_le(monde["m1"], D(2025, 1, 1))
    payer(m, [M(2026, 1)], etat=EtatVersement.EN_ATTENTE)
    s = situation(m, M(2026, 1))
    assert not s.a_jour and s.en_attente == {M(2026, 1)} and s.total_annee == 0


def test_changement_de_tarif(monde, depart):
    Tarif.objects.create(
        date_effet=M(2026, 3),
        montant=150,
        part_paroisse=30,
        part_circuit=20,
        part_region=20,
        part_national=30,
    )
    m = enregistre_le(monde["m1"], D(2025, 1, 1))
    assert tarif_du(M(2026, 2)).montant == 100 and tarif_du(M(2026, 3)).montant == 150
    assert situation(m, M(2026, 4)).reste_du == 100 + 100 + 150 + 150


def test_parts_total_100(db):
    t = Tarif(
        date_effet=M(2027, 1),
        montant=100,
        part_paroisse=30,
        part_circuit=20,
        part_region=20,
        part_national=20,
    )
    with pytest.raises(ValidationError):
        t.full_clean()


def test_tarif_par_defaut_30_20_20_30(db):
    t = tarif_du(M(2026, 1))
    assert (t.montant, t.part_paroisse, t.part_circuit, t.part_region, t.part_national) == (
        100,
        30,
        20,
        20,
        30,
    )


def test_mois_cotise_unique_actif(monde, depart, payer):
    m = monde["m1"]
    v = payer(m, [M(2026, 1)])
    MoisCotise.objects.create(versement=v, membre=m, mois=M(2026, 1), montant=100, actif=False)
    with pytest.raises(IntegrityError), transaction.atomic():
        MoisCotise.objects.create(versement=v, membre=m, mois=M(2026, 1), montant=100, actif=True)


def test_versement_ne_se_supprime_pas(monde, depart, payer):
    v = payer(monde["m1"], [M(2026, 1)])
    with pytest.raises(PermissionDenied):
        v.delete()


def test_situations_groupees_egales_individuelles(
    monde, depart, payer, django_assert_max_num_queries
):
    membres = [enregistre_le(monde[k], D(2025, 1, 1)) for k in ("m1", "m2", "m3", "m4")]
    payer(membres[0], [M(2026, 1), M(2026, 2)])
    payer(membres[1], [M(2026, 1)], etat=EtatVersement.EN_ATTENTE)
    qs = Membre.objects.filter(pk__in=[m.pk for m in membres])
    with django_assert_max_num_queries(6):
        groupees = situations(qs, M(2026, 3))
    for m in membres:
        assert groupees[m.pk] == situation(m, M(2026, 3))
