from datetime import date

import pytest
from django.core.management import call_command

from apps.journal.models import EntreeJournal
from apps.mouvements.models import Sanction
from apps.mouvements.sanctions import appliquer_sanctions, enregistrer_sanction, lever_sanction
from apps.mouvements.services import MouvementRefuse, blocage_rehabilitation, demander_mutation
from apps.notifications.models import Notification

J = date(2026, 11, 11)


def _sanction(monde, membre=None, **kw):
    from apps.comptes.models import Compte

    kw.setdefault("degre", 1)
    kw.setdefault("date_debut", J)
    kw.setdefault("motif", "Faute constatée")
    kw.setdefault("reference", "Décision BNC n° 7")
    kw.setdefault("jour", J)
    par = Compte.objects.get(is_superuser=True)
    return enregistrer_sanction(membre=membre or monde["m1"], par=par, **kw)


def _recharger(m):
    m.refresh_from_db()
    m.compte.refresh_from_db()
    return m


def test_avertissement_sans_changement_de_statut(monde):
    s = _sanction(monde, type="avertissement_ecrit")
    m1 = _recharger(monde["m1"])
    assert m1.statut == "actif" and s.effet is None and not m1.historique.exists()
    assert EntreeJournal.objects.filter(action="sanction").exists()
    for qui in ("sec_p1", "chef", "m1"):
        assert Notification.objects.filter(
            destinataire=monde[qui].compte, message__contains="Avertissement écrit"
        ).exists()


def test_suspension_sanctionne_puis_fin(monde):
    _sanction(monde, type="suspension", date_fin=date(2026, 11, 26))
    m1 = _recharger(monde["m1"])
    assert m1.statut == "sanctionne" and m1.compte.is_active
    assert appliquer_sanctions(date(2026, 11, 25)) == (0, 0)
    assert _recharger(m1).statut == "sanctionne"
    assert appliquer_sanctions(date(2026, 11, 26)) == (0, 1)
    m1 = _recharger(m1)
    assert m1.statut == "actif" and m1.historique.first().motif == "Fin de la sanction"
    assert Sanction.objects.get().membre == m1  # la sanction reste dans l'historique


def test_exclusion_definitive_desactive_et_annule_mutation(monde, compte_technique):
    mut = demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)
    _sanction(monde, type="exclusion_definitive", degre=3)
    m1 = _recharger(monde["m1"])
    mut.refresh_from_db()
    assert m1.statut == "exclu" and not m1.compte.is_active and mut.etat == "annulee"
    assert appliquer_sanctions(date(2030, 1, 1)) == (0, 0)
    assert _recharger(m1).statut == "exclu"


@pytest.mark.parametrize(
    "kw, attendu",
    [
        (dict(type="suspension", date_fin=date(2026, 11, 27)), "15 jours"),
        (dict(type="suspension"), "date de fin"),
        (dict(type="exclusion_temporaire", date_fin=date(2026, 11, 1)), "précéder"),
        (dict(type="autre"), "Précisez"),
        (dict(type="exclusion_definitive", date_fin=date(2027, 1, 1)), "pas de date de fin"),
        (dict(type="avertissement_ecrit", degre=4), "degré"),
        (dict(type="inconnu"), "Type"),
    ],
)
def test_sanctions_refusees(monde, kw, attendu):
    with pytest.raises(MouvementRefuse, match=attendu):
        _sanction(monde, **kw)
    assert not Sanction.objects.exists()


def test_suspension_de_15_jours_acceptee(monde):
    _sanction(monde, type="suspension", date_fin=date(2026, 11, 26))
    assert Sanction.objects.count() == 1


def test_membre_decede_refuse(monde):
    m1 = monde["m1"]
    m1.statut = "decede"
    m1.save()
    with pytest.raises(MouvementRefuse, match="décédé ou démissionnaire"):
        _sanction(monde, type="blame")


def test_fin_suspension_pendant_exclusion(monde):
    _sanction(monde, type="suspension", date_fin=date(2026, 11, 20))
    _sanction(monde, type="exclusion_temporaire", date_fin=date(2027, 11, 11), degre=3)
    assert _recharger(monde["m1"]).statut == "exclu"
    appliquer_sanctions(date(2026, 11, 20))
    assert _recharger(monde["m1"]).statut == "exclu"
    appliquer_sanctions(date(2027, 11, 11))
    assert _recharger(monde["m1"]).statut == "actif"


def test_sanction_future_appliquee_au_jour_dit(monde):
    _sanction(monde, type="retrait", date_debut=date(2026, 12, 1), date_fin=date(2027, 3, 1))
    assert _recharger(monde["m1"]).statut == "actif"
    assert appliquer_sanctions(date(2026, 12, 1)) == (1, 0)
    assert _recharger(monde["m1"]).statut == "sanctionne"


def test_lever_sanction(monde, compte_technique):
    s = _sanction(monde, type="exclusion_definitive", degre=3)
    lever_sanction(sanction=s, motif="Erreur de personne", par=compte_technique, jour=J)
    s.refresh_from_db()
    m1 = _recharger(monde["m1"])
    assert s.levee_le == J and s.motif_levee == "Erreur de personne"
    assert m1.statut == "actif" and m1.compte.is_active
    assert EntreeJournal.objects.filter(action="sanction_levee").exists()
    with pytest.raises(MouvementRefuse, match="déjà levée"):
        lever_sanction(sanction=s, motif="x", par=compte_technique, jour=J)


def test_fin_exclusion_temporaire_permet_rehabilitation_ulterieure(monde):
    _sanction(
        monde,
        type="exclusion_temporaire",
        date_debut=date(2024, 1, 1),
        date_fin=date(2024, 7, 1),
        degre=3,
        jour=date(2024, 1, 1),
    )
    appliquer_sanctions(date(2024, 7, 1))
    _sanction(
        monde,
        type="exclusion_definitive",
        date_debut=date(2025, 1, 1),
        degre=3,
        jour=date(2025, 1, 1),
    )
    assert blocage_rehabilitation(_recharger(monde["m1"]), J) is None


def test_commande(monde):
    _sanction(
        monde,
        type="suspension",
        date_debut=date(2020, 1, 1),
        date_fin=date(2020, 1, 10),
        jour=date(2020, 1, 1),
    )
    assert _recharger(monde["m1"]).statut == "sanctionne"
    call_command("fin_des_sanctions")
    assert _recharger(monde["m1"]).statut == "actif"
