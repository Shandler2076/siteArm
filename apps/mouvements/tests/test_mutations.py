from datetime import date

import pytest

from apps.bureaux.perimetre import Unite, anciens_membres, membres_visibles
from apps.journal.models import EntreeJournal
from apps.mouvements.models import Mutation
from apps.mouvements.services import (
    MouvementRefuse,
    decider_mutation,
    demander_mutation,
    donner_avis,
    mutations_pour_unite,
)
from apps.notifications.models import Notification

J = date(2026, 11, 11)


def _notifs(membre):
    return list(
        Notification.objects.filter(destinataire=membre.compte).values_list("message", flat=True)
    )


def test_demande_notifie_depart_et_bn(monde, compte_technique):
    mut = demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)
    assert mut.etat == "avis" and mut.paroisse_depart == monde["P1"]
    for qui in ("sec_p1", "chef"):
        (msg,) = _notifs(monde[qui])
        assert "Demande de mutation" in msg and monde["m1"].matricule in msg and "P4" in msg
    lien = Notification.objects.filter(destinataire=monde["sec_p1"].compte).get().lien
    assert lien == f"/bureau/mutations/{mut.pk}/"
    assert EntreeJournal.objects.filter(action="mutation_demandee").count() == 1


def test_demandes_refusees(monde, compte_technique):
    m1, m2 = monde["m1"], monde["m2"]
    with pytest.raises(MouvementRefuse, match="déjà dans cette paroisse"):
        demander_mutation(membre=m1, paroisse_arrivee=monde["P1"], par=compte_technique)
    monde["P3"].fermer()
    with pytest.raises(MouvementRefuse, match="fermée"):
        demander_mutation(membre=m1, paroisse_arrivee=monde["P3"], par=compte_technique)
    m2.statut = "decede"
    m2.save()
    with pytest.raises(MouvementRefuse, match="actif ou sanctionné"):
        demander_mutation(membre=m2, paroisse_arrivee=monde["P4"], par=compte_technique)
    demander_mutation(membre=m1, paroisse_arrivee=monde["P4"], par=compte_technique)
    with pytest.raises(MouvementRefuse, match="déjà en cours"):
        demander_mutation(membre=m1, paroisse_arrivee=monde["P2"], par=compte_technique)
    assert Mutation.objects.count() == 1


def test_avis_puis_attente_bn(monde, compte_technique):
    mut = demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)
    donner_avis(
        mutation=mut, niveau="circuit", favorable=False, commentaire="Non", par=monde["chef"].compte
    )
    mut.refresh_from_db()
    assert mut.etat == "avis"
    with pytest.raises(MouvementRefuse, match="circuit a déjà été donné"):
        donner_avis(
            mutation=mut, niveau="circuit", favorable=True, commentaire="", par=monde["chef"].compte
        )
    donner_avis(mutation=mut, niveau="region", favorable=True, commentaire="", par=compte_technique)
    mut.refresh_from_db()
    assert mut.etat == "bn" and mut.avis.count() == 2


def test_validation_met_a_jour_parcours(monde, compte_technique):
    m1 = monde["m1"]
    mut = demander_mutation(membre=m1, paroisse_arrivee=monde["P4"], par=compte_technique)
    decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    ancienne, nouvelle = m1.affectations.order_by("date_debut", "pk")
    assert ancienne.date_fin == J and nouvelle.date_fin is None and nouvelle.date_debut == J
    assert (nouvelle.paroisse, nouvelle.circuit_a_date, nouvelle.region_a_date) == (
        monde["P4"],
        monde["Dangbo A"],
        monde["WEME"],
    )
    assert nouvelle.motif == f"Mutation n° {mut.pk}"
    mut.refresh_from_db()
    assert mut.etat == "validee" and mut.decidee_par == compte_technique
    assert membres_visibles(Unite("paroisse", monde["P4"])).filter(pk=m1.pk).exists()
    assert not membres_visibles(Unite("paroisse", monde["P1"])).filter(pk=m1.pk).exists()
    assert anciens_membres(Unite("paroisse", monde["P1"])).filter(membre=m1).exists()
    assert anciens_membres(Unite("region", monde["HOULENOU"])).filter(membre=m1).exists()
    assert any("Mutation validée" in m for m in _notifs(m1))
    assert any("Mutation validée" in m for m in _notifs(monde["chef"]))
    assert EntreeJournal.objects.filter(action="mutation_decidee").count() == 1


def test_validation_sans_avis_possible(monde, compte_technique):
    mut = demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P2"], par=compte_technique)
    assert mut.etat == "avis"
    decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    assert monde["m1"].affectation_actuelle.paroisse == monde["P2"]


def test_refus_aucun_changement(monde, compte_technique):
    m1 = monde["m1"]
    mut = demander_mutation(membre=m1, paroisse_arrivee=monde["P4"], par=compte_technique)
    decider_mutation(mutation=mut, valider=False, par=compte_technique, commentaire="Non", jour=J)
    mut.refresh_from_db()
    assert mut.etat == "refusee" and mut.commentaire_decision == "Non"
    assert m1.affectations.count() == 1 and m1.affectation_actuelle.paroisse == monde["P1"]
    assert any("Mutation refusée" in m for m in _notifs(m1))


def test_mandats_clos_dans_unites_quittees(monde, compte_technique):
    sec, chef = monde["sec_p1"], monde["chef"]
    mut = demander_mutation(membre=sec, paroisse_arrivee=monde["P2"], par=compte_technique)
    decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    assert not sec.mandats.en_cours(J).exists()
    mut = demander_mutation(membre=chef, paroisse_arrivee=monde["P1"], par=compte_technique)
    decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    assert chef.mandats.en_cours(J).exists()  # même circuit : mandat de circuit conservé


def test_decision_deux_fois(monde, compte_technique):
    m1 = monde["m1"]
    mut = demander_mutation(membre=m1, paroisse_arrivee=monde["P4"], par=compte_technique)
    decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    with pytest.raises(MouvementRefuse, match="déjà été traitée"):
        decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    assert m1.affectations.filter(date_fin__isnull=True).count() == 1
    assert m1.affectations.count() == 2


def test_validation_situation_changee(monde, compte_technique):
    m1 = monde["m1"]
    mut = demander_mutation(membre=m1, paroisse_arrivee=monde["P4"], par=compte_technique)
    m1.statut = "decede"
    m1.save()
    with pytest.raises(MouvementRefuse, match="La situation du membre a changé"):
        decider_mutation(mutation=mut, valider=True, par=compte_technique, jour=J)
    mut.refresh_from_db()
    assert mut.etat == "avis" and m1.affectations.count() == 1


def test_mutations_pour_unite(monde, compte_technique):
    mut = demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)
    assert list(mutations_pour_unite(Unite("paroisse", monde["P4"]))) == [mut]
    assert list(mutations_pour_unite(Unite("circuit", monde["Ekpe A"]))) == [mut]
    assert list(mutations_pour_unite(Unite("paroisse", monde["P3"]))) == []
    assert list(mutations_pour_unite(Unite("national", None))) == [mut]
