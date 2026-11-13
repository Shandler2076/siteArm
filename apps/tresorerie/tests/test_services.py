"""Trésorerie : paiements mobile money (simulés), cotisations spéciales, reversements."""

import datetime

import pytest
from django.utils import timezone

from apps.cotisations.models import EtatVersement, ModeVersement, Versement
from apps.tresorerie import services as s
from apps.tresorerie.models import Contribution, EtatPaiement, EtatReversement, Reversement


def test_payer_ses_mois_par_mobile_money(tresoriers, ouvert, django_capture_on_commit_callbacks):
    m1 = tresoriers["m1"]
    p = s.initier_paiement_mensuel(m1.compte, [(m1, 2)])
    assert p.montant == 200 and p.etat == EtatPaiement.EN_ATTENTE
    with django_capture_on_commit_callbacks(execute=True):
        s.confirmer_paiement(p)
    v = Versement.objects.get(membre=m1)
    assert v.etat == EtatVersement.VALIDE and v.mode == ModeVersement.MOBILE_MONEY
    assert v.numero_recu and v.parts == {
        "paroisse": 60,
        "circuit": 40,
        "region": 40,
        "national": 60,
    }
    assert v.mois.count() == 2
    # Idempotent : une seconde confirmation ne paie pas deux fois.
    s.confirmer_paiement(p)
    assert Versement.objects.filter(membre=m1).count() == 1


def test_payer_pour_un_autre_membre(tresoriers, ouvert, django_capture_on_commit_callbacks):
    m1, m2 = tresoriers["m1"], tresoriers["m2"]
    p = s.initier_paiement_mensuel(m2.compte, [(m1, 1)])
    with django_capture_on_commit_callbacks(execute=True):
        s.confirmer_paiement(p)
    v = Versement.objects.get(membre=m1)
    assert v.saisi_par == m2.compte
    assert m1.compte.notifications.filter(message__contains="payée par mobile money").exists()
    # La paroisse du membre aidé est avertie (pour remettre le reçu imprimé).
    assert (
        tresoriers["sec_p1"].compte.notifications.filter(message__contains="autre membre").exists()
    )


def test_paiement_en_conflit_devient_anomalie(tresoriers, ouvert):
    m1 = tresoriers["m1"]
    p1 = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    p2 = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])  # même mois, initié avant confirmation
    s.confirmer_paiement(p1)
    p2 = s.confirmer_paiement(p2)
    assert p2.etat == EtatPaiement.ANOMALIE and Versement.objects.filter(membre=m1).count() == 1


def test_cotisation_speciale_fixe_en_plusieurs_fois(tresoriers, compte_technique):
    m1 = tresoriers["m1"]
    cs = s.creer_cotisation_speciale(
        libelle="Construction du siège", type_montant="fixe", montant=5000, par=compte_technique
    )
    assert s.concerne_membre(cs, m1)
    s.confirmer_paiement(s.initier_paiement_special(m1.compte, cs, 2000, membre=m1))
    assert s.reste_a_payer(cs, membre=m1) == 3000 and not s.est_reglee(cs, membre=m1)
    with pytest.raises(s.TresorerieRefusee):
        s.initier_paiement_special(m1.compte, cs, 4000, membre=m1)
    s.confirmer_paiement(s.initier_paiement_special(m1.compte, cs, 3000, membre=m1))
    assert s.est_reglee(cs, membre=m1)
    q1, q2 = Contribution.objects.order_by("pk").values_list("quittance", flat=True)
    assert q1.endswith("000001") and q2.endswith("000002")


def test_cotisation_speciale_minimum_libre_et_cible(tresoriers, compte_technique):
    m1, m4 = tresoriers["m1"], tresoriers["m4"]
    region = tresoriers["HOULENOU"].pk
    cs = s.creer_cotisation_speciale(
        libelle="Pèlerinage",
        type_montant="minimum",
        montant=1000,
        pour_membres="certains",
        criteres={"region": str(region)},
        par=compte_technique,
    )
    assert s.concerne_membre(cs, m1) and not s.concerne_membre(cs, m4)
    s.confirmer_paiement(s.initier_paiement_special(m1.compte, cs, 1500, membre=m1))
    assert s.est_reglee(cs, membre=m1)
    don = s.creer_cotisation_speciale(libelle="Don", type_montant="libre", par=compte_technique)
    assert s.reste_a_payer(don, membre=m1) is None


def test_cotisation_demandee_aux_bureaux(tresoriers, compte_technique):
    from apps.bureaux.perimetre import Unite

    cs = s.creer_cotisation_speciale(
        libelle="Contribution des paroisses",
        type_montant="fixe",
        montant=10000,
        pour_membres="aucun",
        pour_bureaux=["paroisse"],
        par=compte_technique,
    )
    p1 = Unite("paroisse", tresoriers["P1"])
    assert s.concerne_unite(cs, p1) and not s.concerne_membre(cs, tresoriers["m1"])
    tres = tresoriers["tresorier"]
    s.confirmer_paiement(s.initier_paiement_special(tres.compte, cs, 10000, unite=p1))
    c = Contribution.objects.get()
    assert c.unite_libelle == p1.libelle and c.membre is None
    assert s.est_reglee(cs, unite_cle=p1.cle)


def test_reversements_prepares_valides_envoyes(tresoriers, ouvert, monkeypatch):
    from apps.bureaux.perimetre import Unite

    m1 = tresoriers["m1"]
    s.confirmer_paiement(s.initier_paiement_mensuel(m1.compte, [(m1, 2)]))
    mois = timezone.localdate().replace(day=1)
    tn, pres = tresoriers["tresorier_national"].compte, tresoriers["president"].compte
    with pytest.raises(s.TresorerieRefusee):  # mois pas encore terminé
        s.preparer_reversements(mois, par=tn)
    plus_tard = timezone.localdate() + datetime.timedelta(days=40)
    monkeypatch.setattr(s.timezone, "localdate", lambda *a: plus_tard)
    faits = {r.cle: r for r in s.preparer_reversements(mois, par=tn)}
    p1 = Unite("paroisse", tresoriers["P1"])
    assert faits[p1.cle].montant == 60 and faits[f"circuit-{tresoriers['Ekpe A'].pk}"].montant == 40
    with pytest.raises(s.TresorerieRefusee):  # pas encore validé
        s.marquer_envoye(faits[p1.cle], reference="MP123", par=tn)
    assert s.valider_reversements(mois, par=pres) == 3
    with pytest.raises(s.TresorerieRefusee):  # pas de numéro enregistré
        s.marquer_envoye(faits[p1.cle], reference="MP123", par=tn)
    s.enregistrer_numero(p1, numero="0197112233", par=tn)
    r = s.marquer_envoye(faits[p1.cle], reference="MP123", par=tn)
    assert r.etat == EtatReversement.ENVOYE and r.numero == "0197112233"
    assert Reversement.objects.filter(etat=EtatReversement.VALIDE).count() == 2


def test_tresorier_ou_chef_par_interim(tresoriers):
    from apps.bureaux.perimetre import Unite, unites_tresorerie
    from apps.bureaux.perimetre import tresoriers as tres

    p1 = Unite("paroisse", tresoriers["P1"])
    assert list(tres(p1)) == [tresoriers["tresorier"].compte]
    # Secrétaire de P1 : lecture seule.
    assert unites_tresorerie(tresoriers["sec_p1"].compte) == [(p1, False)]
    # Circuit sans Trésorier : le Chef assure l'intérim.
    circuit = Unite("circuit", tresoriers["Ekpe A"])
    assert list(tres(circuit)) == [tresoriers["chef"].compte]
