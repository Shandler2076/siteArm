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
    from apps.tresorerie.models import Paiement

    p1 = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    # p1 abandonné depuis plus de 30 minutes : sa réservation tombe, p2 reprend le même mois.
    Paiement.objects.filter(pk=p1.pk).update(
        date_creation=timezone.now() - datetime.timedelta(hours=1)
    )
    p2 = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    assert p2.objet["lignes"][0]["mois"] == p1.objet["lignes"][0]["mois"]
    s.confirmer_paiement(p1)  # confirmé tardivement par la plateforme
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
    assert c.unite_libelle == "Bureau de l'unité paroissiale de P1" and c.membre is None
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


# --- Corrections de la relecture finale ---------------------------------------------------------


def test_mobile_money_ne_compte_pas_dans_les_parts_dues_par_la_paroisse(tresoriers, ouvert):
    from apps.cotisations.services import part_due

    m1 = tresoriers["m1"]
    s.confirmer_paiement(s.initier_paiement_mensuel(m1.compte, [(m1, 1)]))
    mois = timezone.localdate().replace(day=1)
    assert part_due("circuit", tresoriers["P1"], mois) == 0


def test_paiements_simultanes_ne_paient_pas_deux_fois_le_meme_mois(tresoriers, ouvert):
    m1, m2 = tresoriers["m1"], tresoriers["m2"]
    p1 = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    p2 = s.initier_paiement_mensuel(m2.compte, [(m1, 1)])  # aide simultanée
    assert p1.objet["lignes"][0]["mois"] != p2.objet["lignes"][0]["mois"]
    assert s.confirmer_paiement(p1).etat == EtatPaiement.CONFIRME
    assert s.confirmer_paiement(p2).etat == EtatPaiement.CONFIRME


def test_cotisation_fixe_deux_paiements_en_cours_ne_depassent_pas(tresoriers, compte_technique):
    m1 = tresoriers["m1"]
    cs = s.creer_cotisation_speciale(
        libelle="Siège", type_montant="fixe", montant=1000, par=compte_technique
    )
    s.initier_paiement_special(m1.compte, cs, 1000, membre=m1)
    with pytest.raises(s.TresorerieRefusee):
        s.initier_paiement_special(m1.compte, cs, 500, membre=m1)


def test_montant_change_entre_temps_devient_anomalie(tresoriers, ouvert):
    from apps.tresorerie.models import Paiement

    m1 = tresoriers["m1"]
    p = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    Paiement.objects.filter(pk=p.pk).update(montant=150)  # tarif changé entre-temps
    p.refresh_from_db()
    assert s.confirmer_paiement(p).etat == EtatPaiement.ANOMALIE
    assert not Versement.objects.filter(membre=m1).exists()


def test_paiement_simule_ferme_hors_site_d_essai(tresoriers, ouvert, settings):
    m1 = tresoriers["m1"]
    p = s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    settings.PAIEMENT_SIMULE = False
    with pytest.raises(s.TresorerieRefusee):
        s.initier_paiement_mensuel(m1.compte, [(m1, 1)])
    with pytest.raises(s.TresorerieRefusee):
        s.confirmer_paiement(p)


def test_qui_prepare_ne_valide_pas_et_pas_de_raccourci_technique(
    tresoriers, ouvert, compte_technique, monkeypatch
):
    from apps.bureaux.perimetre import est_tresorier_national, est_validateur_reversements

    assert not est_tresorier_national(compte_technique)
    assert not est_validateur_reversements(compte_technique)
    m1 = tresoriers["m1"]
    s.confirmer_paiement(s.initier_paiement_mensuel(m1.compte, [(m1, 1)]))
    mois = timezone.localdate().replace(day=1)
    plus_tard = timezone.localdate() + datetime.timedelta(days=40)
    monkeypatch.setattr(s.timezone, "localdate", lambda *a: plus_tard)
    tn = tresoriers["tresorier_national"].compte
    s.preparer_reversements(mois, par=tn)
    with pytest.raises(s.TresorerieRefusee):
        s.valider_reversements(mois, par=tn)


def test_lien_de_notification_externe_refuse(tresoriers):
    from apps.notifications.services import resoudre_lien

    compte = tresoriers["m1"].compte
    for lien in ("//exemple.org/", "/\\exemple.org/", "https://exemple.org/"):
        assert resoudre_lien(compte, lien) is None


# --- Cibles et montants (13/11/2026) ------------------------------------------------------------


def test_unite_paie_ensemble_et_quittance_distincte(tresoriers, compte_technique):
    from apps.bureaux.perimetre import Unite

    cs = s.creer_cotisation_speciale(
        libelle="Contribution des unités",
        type_montant="fixe",
        montant=50000,
        pour_membres="aucun",
        pour_unites=["paroisse"],
        pour_bureaux=["paroisse"],
        par=compte_technique,
    )
    p1 = Unite("paroisse", tresoriers["P1"])
    tres = tresoriers["tresorier"].compte
    s.confirmer_paiement(s.initier_paiement_special(tres, cs, 50000, unite=p1, type_payeur="unite"))
    s.confirmer_paiement(s.initier_paiement_special(tres, cs, 1000, unite=p1, type_payeur="bureau"))
    libelles = sorted(Contribution.objects.values_list("unite_libelle", flat=True))
    assert libelles == ["Bureau de l'unité paroissiale de P1", "Unité paroissiale de P1"]
    assert s.est_reglee(cs, unite_cle=s.cle_payeur("unite", p1))
    assert not s.est_reglee(cs, unite_cle=s.cle_payeur("bureau", p1))
    types = {x["type"] for x in s.speciales_du_bureau(p1)}
    assert types == {"unite", "bureau"}


def test_certains_membres_designes_et_membres_des_bureaux(tresoriers, compte_technique):
    cs = s.creer_cotisation_speciale(
        libelle="Ciblée",
        type_montant="fixe",
        montant=500,
        pour_membres="certains",
        membres_designes=[tresoriers["m4"].pk],
        membres_des_bureaux=["paroisse"],
        par=compte_technique,
    )
    assert s.concerne_membre(cs, tresoriers["m4"])  # désigné
    assert s.concerne_membre(cs, tresoriers["sec_p1"])  # membre d'un bureau de paroisse
    assert not s.concerne_membre(cs, tresoriers["m1"])
    with pytest.raises(s.TresorerieRefusee):
        s.creer_cotisation_speciale(
            libelle="Vide",
            type_montant="fixe",
            montant=1,
            pour_membres="certains",
            par=compte_technique,
        )


def test_montant_libre_avec_suggestion(tresoriers, compte_technique):
    cs = s.creer_cotisation_speciale(
        libelle="Don", type_montant="libre", montant_suggere=2000, par=compte_technique
    )
    assert cs.montant is None and cs.montant_suggere == 2000


def test_amende_liee_a_la_sanction(tresoriers, compte_technique):
    from apps.mouvements.sanctions import enregistrer_sanction

    m1 = tresoriers["m1"]
    sanction = enregistrer_sanction(
        membre=m1,
        degre=1,
        type="amende",
        date_debut=timezone.localdate(),
        motif="Retards",
        reference="BNC-12",
        par=compte_technique,
        amende=3000,
    )
    amende = sanction.amendes.get()
    assert s.concerne_membre(amende, m1) and not s.concerne_membre(amende, tresoriers["m2"])
    from apps.bureaux.perimetre import Unite

    assert amende not in [
        x["cs"] for x in s.speciales_du_bureau(Unite("paroisse", tresoriers["P1"]))
    ]
