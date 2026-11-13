from datetime import date

import pytest

from apps.journal.models import EntreeJournal
from apps.mouvements.models import HistoriqueMembre, Signalement
from apps.mouvements.services import (
    MouvementRefuse,
    blocage_rehabilitation,
    decider_signalement,
    demander_mutation,
    signaler,
)
from apps.mouvements.statuts import changer_statut
from apps.notifications.models import Notification

J = date(2026, 11, 11)


def _sig(monde, membre=None, **kw):
    kw.setdefault("par", monde["sec_p1"].compte)
    kw.setdefault("unite", f"paroisse-{monde['P1'].pk}")
    kw.setdefault("jour", J)
    return signaler(membre=membre or monde["m1"], **kw)


def _decider(sig, confirmer=True, jour=J, **kw):
    from apps.comptes.models import Compte

    par = Compte.objects.get(is_superuser=True)
    return decider_signalement(signalement=sig, confirmer=confirmer, par=par, jour=jour, **kw)


def _demissionnaire(membre, le):
    changer_statut(membre, "demissionnaire", par=None, date_effet=le, motif="Démission")


def test_deces_signale_puis_confirme(monde):
    m1 = monde["m1"]
    sig = _sig(monde, type="deces", date_effet=date(2026, 11, 1))
    assert sig.etat == "bn" and EntreeJournal.objects.filter(action="signalement").exists()
    d = _decider(sig)
    m1.refresh_from_db()
    m1.compte.refresh_from_db()
    assert d.pdf is None and d.signalement.etat == "validee"
    assert m1.statut == "decede" and not m1.compte.is_active
    (h,) = m1.historique.all()
    assert h.date_effet == date(2026, 11, 1) and h.nouveau == "decede"
    for qui in ("sec_p1", "chef"):
        assert Notification.objects.filter(
            destinataire=monde[qui].compte, message__contains="Décès confirmé"
        ).exists()
    assert EntreeJournal.objects.filter(action="signalement_decide").exists()


def test_demission_confirmee(monde):
    m1 = monde["m1"]
    matricule = m1.matricule
    _decider(_sig(monde, type="demission", date_effet=date(2026, 10, 1), reference="Lettre 12"))
    m1.refresh_from_db()
    assert m1.statut == "demissionnaire" and not m1.compte.is_active
    assert m1.matricule == matricule and m1.historique.get().reference == "Lettre 12"


def test_signalements_refuses(monde):
    m1 = monde["m1"]
    m1.date_naissance = date(1990, 5, 1)
    m1.save()
    cas = [
        (dict(type="deces", date_effet=date(2026, 11, 12)), "futur"),
        (dict(type="deces", date_effet=date(1980, 1, 1)), "naissance"),
        (dict(type="deces"), "date"),
        (dict(type="categorie", nouvelle_categorie="honneur"), "Procédure supprimée"),
        (dict(type="rehabilitation"), "démissionnaire ou exclu"),
    ]
    for kw, attendu in cas:
        with pytest.raises(MouvementRefuse, match=attendu):
            _sig(monde, **kw)
    _sig(monde, type="deces", date_effet=date(2026, 11, 1))
    with pytest.raises(MouvementRefuse, match="déjà en attente"):
        _sig(monde, type="deces", date_effet=date(2026, 11, 2))
    m2 = monde["m2"]
    m2.statut = "decede"
    m2.save()
    with pytest.raises(MouvementRefuse, match="actif ou sanctionné"):
        _sig(monde, membre=m2, type="demission", date_effet=date(2026, 1, 1))
    assert Signalement.objects.count() == 1


def test_deces_annule_mutation(monde, compte_technique):
    mut = demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)
    _decider(_sig(monde, type="deces", date_effet=date(2026, 11, 1)))
    mut.refresh_from_db()
    assert mut.etat == "annulee" and "décès" in mut.commentaire_decision


@pytest.mark.parametrize("jour, possible", [(date(2027, 2, 27), False), (date(2027, 2, 28), True)])
def test_delai_six_mois_bornes(monde, jour, possible):
    m1 = monde["m1"]
    _demissionnaire(m1, date(2026, 8, 31))
    blocage = blocage_rehabilitation(m1, jour)
    if possible:
        assert blocage is None
    else:
        assert "à partir du 28/02/2027" in blocage


def test_rehabilitation_valide(monde):
    m1 = monde["m1"]
    _demissionnaire(m1, date(2026, 1, 1))
    ancien_hash = m1.compte.password
    sig = _sig(monde, type="rehabilitation")
    d = _decider(sig)
    m1.refresh_from_db()
    m1.compte.refresh_from_db()
    assert d.pdf.startswith(b"%PDF")
    assert m1.statut == "actif" and m1.compte.is_active and m1.compte.doit_changer_mot_de_passe
    assert m1.compte.password != ancien_hash
    assert m1.historique.first().nouveau == "actif"


def test_rehabilitation_exclu_exige_engagement(monde):
    m1 = monde["m1"]
    changer_statut(m1, "exclu", par=None, date_effet=date(2025, 1, 1), motif="Exclusion")
    with pytest.raises(MouvementRefuse, match="engagement écrit de bonne conduite"):
        _sig(monde, type="rehabilitation")
    sig = _sig(monde, type="rehabilitation", reference="Engagement n° 4")
    _decider(sig)
    m1.refresh_from_db()
    assert m1.statut == "actif" and m1.historique.first().reference == "Engagement n° 4"


def test_exclu_deux_fois_bloque(monde):
    m1 = monde["m1"]
    changer_statut(m1, "exclu", par=None, date_effet=date(2024, 1, 1), motif="Exclusion")
    changer_statut(
        m1, "actif", par=None, date_effet=date(2024, 9, 1), motif="Réhabilitation validée"
    )
    changer_statut(m1, "exclu", par=None, date_effet=date(2025, 1, 1), motif="Exclusion")
    assert "art. 172" in blocage_rehabilitation(m1, J)
    with pytest.raises(MouvementRefuse, match="art. 172"):
        _sig(monde, type="rehabilitation", reference="X")


def test_date_inconnue_bloque(monde):
    m1 = monde["m1"]
    m1.statut = "demissionnaire"
    m1.save()
    assert "Date de démission ou d'exclusion inconnue" in blocage_rehabilitation(m1, J)


def test_admission_comme_actif_notifiee(monde, compte_technique):
    from apps.membres.models import Membre
    from apps.mouvements.statuts import admettre_comme_actif

    m1 = monde["m1"]
    Membre.objects.filter(pk=m1.pk).update(categorie="sympathisant")
    m1.refresh_from_db()
    admettre_comme_actif(
        m1, date_effet=date(2026, 11, 1), reference="D-1", motif="", par=compte_technique
    )
    m1.refresh_from_db()
    assert m1.categorie == "actif" and m1.historique.get().type == "categorie"


def test_confirmer_deux_fois(monde):
    sig = _sig(monde, type="deces", date_effet=date(2026, 11, 1))
    _decider(sig)
    with pytest.raises(MouvementRefuse, match="déjà été traitée"):
        _decider(sig)
    assert HistoriqueMembre.objects.count() == 1


def test_refus_signalement(monde):
    m1 = monde["m1"]
    sig = _sig(monde, type="deces", date_effet=date(2026, 11, 1))
    _decider(sig, confirmer=False, motif_refus="Erreur de personne")
    sig.refresh_from_db()
    m1.refresh_from_db()
    assert sig.etat == "refusee" and sig.motif_refus == "Erreur de personne"
    assert m1.statut == "actif" and not m1.historique.exists()
    assert Notification.objects.filter(
        destinataire=monde["sec_p1"].compte, message__contains="refusé"
    ).exists()


def test_rehabilitation_revérifiee_a_la_decision(monde):
    m1 = monde["m1"]
    _demissionnaire(m1, date(2026, 1, 1))
    sig = _sig(monde, type="rehabilitation", jour=date(2026, 8, 1))
    with pytest.raises(MouvementRefuse, match="à partir du"):
        _decider(sig, jour=date(2026, 6, 1))
