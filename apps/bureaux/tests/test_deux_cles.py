"""Deux clés et délégation (décisions du 19/11/2026)."""

import datetime

import pytest
from django.test import Client
from django.utils import timezone

from apps.bureaux import deux_cles as dc
from apps.bureaux.models import Delegation, DemandeValidation, Fonction, Mandat
from apps.notifications.models import Notification

Etat = DemandeValidation.Etat


def _client(m):
    c = Client()
    c.force_login(m.compte)
    return c


@pytest.fixture
def bnc(monde, nouveau_membre, donner_mandat):
    r = {}
    for nom, fonction in [
        ("pres", "Président"),
        ("vp", "Vice-président"),
        ("sn", "Secrétaire national"),
        ("sna", "Secrétaire national adjoint"),
    ]:
        r[nom] = nouveau_membre(monde["P1"], nom.upper())
        donner_mandat(r[nom], fonction)
    return dict(monde, **r)


def _installer_p1(bnc):
    f = Fonction.objects.get(nom="Chef d'Unité paroissiale")
    return {
        "unite": f"paroisse-{bnc['P1'].pk}",
        "titulaires": {str(f.pk): bnc["m1"].matricule},
        "date_debut": "2026-02-01",
    }


def _chef_p1():
    return Mandat.objects.filter(fonction__nom="Chef d'Unité paroissiale").exists()


def test_le_secretaire_prepare_le_president_valide(bnc):
    demande, res = dc.soumettre_ou_executer(
        bnc["sn"].compte, "installer", _installer_p1(bnc), "Installer le bureau de P1"
    )
    assert res is None and demande.etat == Etat.ATTENTE and not _chef_p1()
    assert Notification.objects.filter(destinataire=bnc["pres"].compte).exists()
    with pytest.raises(dc.DeuxClesRefusee):
        dc.valider(demande, par=bnc["sn"].compte)  # pas lui-même
    with pytest.raises(dc.DeuxClesRefusee):
        dc.valider(demande, par=bnc["vp"].compte)  # Président en fonction, moins de 7 jours
    demande = dc.valider(demande, par=bnc["pres"].compte)
    assert demande.etat == Etat.VALIDEE and demande.qualite == "Président" and _chef_p1()


def test_le_president_agit_seul_et_le_secretaire_est_informe(
    bnc, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        demande, _ = dc.soumettre_ou_executer(
            bnc["pres"].compte, "installer", _installer_p1(bnc), "Installer le bureau de P1"
        )
    assert demande is None and _chef_p1()
    assert Notification.objects.filter(
        destinataire=bnc["sn"].compte, message__contains="le Président a fait"
    ).exists()


def test_vice_president_si_poste_vacant_ou_apres_7_jours(bnc):
    demande, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "X")
    DemandeValidation.objects.filter(pk=demande.pk).update(
        date=timezone.now() - datetime.timedelta(days=8)
    )
    demande.refresh_from_db()
    assert "7 jours" in dc.qualite_pour_valider(bnc["vp"].compte, demande)
    bnc["pres"].mandats.update(date_fin=datetime.date.today())
    demande2, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "Y")
    assert "vacant" in dc.qualite_pour_valider(bnc["vp"].compte, demande2)


def test_refus_avec_motif_et_expiration(bnc):
    d1, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "X")
    with pytest.raises(dc.DeuxClesRefusee):
        dc.refuser(d1, par=bnc["pres"].compte, motif="")
    assert dc.refuser(d1, par=bnc["pres"].compte, motif="Pas maintenant").etat == Etat.REFUSEE
    d2, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "Y")
    DemandeValidation.objects.filter(pk=d2.pk).update(
        date=timezone.now() - datetime.timedelta(days=31)
    )
    assert dc.expirer_demandes() == 1
    with pytest.raises(dc.DeuxClesRefusee):
        dc.valider(d2, par=bnc["pres"].compte)


def test_echec_si_la_situation_a_change(bnc):
    from apps.mouvements.statuts import changer_statut

    d, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "X")
    changer_statut(
        bnc["m1"],
        "demissionnaire",
        par=bnc["pres"].compte,
        date_effet=datetime.date.today(),
        motif="test",
    )
    d = dc.valider(d, par=bnc["pres"].compte)
    assert d.etat == Etat.ECHEC and "actif" in d.motif and not _chef_p1()


def test_delegation(bnc):
    fin = timezone.now() + datetime.timedelta(hours=72)
    with pytest.raises(dc.DeuxClesRefusee):
        dc.deleguer(
            president=bnc["sn"].compte, delegataire=bnc["vp"].compte, objet="deux_cles", fin=fin
        )
    deleg = dc.deleguer(
        president=bnc["pres"].compte, delegataire=bnc["sna"].compte, objet="deux_cles", fin=fin
    )
    d, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "X")
    assert dc.qualite_pour_valider(bnc["sna"].compte, d) == "sur délégation du Président"
    dc.retirer_delegation(deleg, par=bnc["pres"].compte)
    assert dc.qualite_pour_valider(bnc["sna"].compte, d) == ""
    assert Delegation.objects.get().retiree_le is not None


def test_delegation_des_reversements(bnc):
    from apps.bureaux.perimetre import est_validateur_reversements

    assert not est_validateur_reversements(bnc["sna"].compte)
    dc.deleguer(
        president=bnc["pres"].compte,
        delegataire=bnc["sna"].compte,
        objet="reversements",
        fin=timezone.now() + datetime.timedelta(days=1),
    )
    assert est_validateur_reversements(bnc["sna"].compte)


def test_pages(bnc):
    f = Fonction.objects.get(nom="Chef d'Unité paroissiale")
    sn = _client(bnc["sn"])
    r = sn.post(
        "/bureau/bn/installer/",
        {
            "niveau": "paroisse",
            "unite": bnc["P1"].pk,
            "date_debut": "2026-02-01",
            f"fonction_{f.pk}": bnc["m1"].matricule,
        },
        follow=True,
    )
    assert "en attente de validation" in r.content.decode() and not _chef_p1()
    d = DemandeValidation.objects.get()
    pres = _client(bnc["pres"])
    page = pres.get("/bureau/bn/validations/").content.decode()
    assert f"/bureau/bn/validations/{d.pk}/valider/" in page
    pres.post(f"/bureau/bn/validations/{d.pk}/valider/")
    assert _chef_p1()
    page = pres.get("/bureau/bn/delegations/").content.decode()
    assert "Déléguer" in page
    r = pres.post(
        "/bureau/bn/delegations/",
        {"delegataire": bnc["sna"].matricule, "objet": "deux_cles", "heures": "72"},
    )
    assert r.status_code == 302 and Delegation.objects.exists()


def test_double_verification_pour_les_validateurs(bnc):
    """Relecture : le Vice-président et un délégataire valident : code à 6 chiffres exigé."""
    from django.test import override_settings

    from apps.securite.services import doit_verifier

    with override_settings(DOUBLE_VERIFICATION_BN=True):
        assert doit_verifier(type(bnc["vp"].compte).objects.get(pk=bnc["vp"].compte.pk))
        assert doit_verifier(type(bnc["sna"].compte).objects.get(pk=bnc["sna"].compte.pk))


def test_le_secretaire_qui_a_perdu_sa_fonction(bnc):
    """Relecture : à la validation, l'auteur doit encore être Secrétaire national."""
    d, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", _installer_p1(bnc), "X")
    bnc["sn"].mandats.update(date_fin=datetime.date.today())
    d = dc.valider(d, par=bnc["pres"].compte)
    assert d.etat == Etat.ECHEC and not _chef_p1()


def test_erreur_imprevue_marquee_echec(bnc):
    """Relecture : une donnée disparue ne bloque pas la demande (pas d'erreur 500)."""
    donnees = _installer_p1(bnc)
    d, _ = dc.soumettre_ou_executer(bnc["sn"].compte, "installer", donnees, "X")
    DemandeValidation.objects.filter(pk=d.pk).update(
        donnees={**donnees, "titulaires": {"999999": bnc["m1"].matricule}}
    )
    assert dc.valider(d, par=bnc["pres"].compte).etat == Etat.ECHEC


def test_pas_de_validation_de_sa_propre_nomination(bnc):
    """Relecture : le Vice-président ne valide pas une action qui le nomme lui-même."""
    pres = Mandat.objects.get(membre=bnc["pres"])
    d, _ = dc.soumettre_ou_executer(
        bnc["sn"].compte,
        "remplacer",
        {
            "mandat": pres.pk,
            "date": "2026-06-01",
            "motif": "demission",
            "remplacant": bnc["vp"].matricule,
        },
        "Remplacer le Président par le Vice-président",
    )
    DemandeValidation.objects.filter(pk=d.pk).update(
        date=timezone.now() - datetime.timedelta(days=8)
    )
    d.refresh_from_db()
    assert dc.qualite_pour_valider(bnc["vp"].compte, d) == ""


def test_circuit_complet_des_actions_par_le_secretaire(bnc, nouveau_membre):
    """Aller-retour des données pour chaque action préparée par le Secrétaire."""
    import json

    from apps.mouvements.models import Sanction

    nouveau = nouveau_membre(bnc["P1"], "Nouveau")
    pres_mandat = Mandat.objects.get(membre=bnc["pres"])
    tn = Fonction.objects.get(nom="Trésorier national")
    actions = [
        (
            "pourvoir",
            {
                "unite": "national",
                "fonction": tn.pk,
                "membre": nouveau.matricule,
                "date_debut": datetime.date.today().isoformat(),
            },
        ),
        ("droits", {"fonction": tn.pk, "case": "droit_grades", "valeur": True}),
        (
            "sanction",
            {
                "membre": bnc["m2"].matricule,
                "champs": {
                    "degre": 1,
                    "type": "avertissement_ecrit",
                    "date_debut": "2026-11-01",
                    "date_fin": None,
                    "motif": "Retards",
                    "reference": "BNC-1",
                    "precision": "",
                    "amende": None,
                },
            },
        ),
    ]
    for action, donnees in actions:
        json.dumps(donnees)  # les données doivent passer en JSON
        d, _ = dc.soumettre_ou_executer(bnc["sn"].compte, action, donnees, action)
        d = dc.valider(d, par=bnc["pres"].compte)
        assert d.etat == Etat.VALIDEE, (action, d.motif)
    sanction = Sanction.objects.get()
    d, _ = dc.soumettre_ou_executer(
        bnc["sn"].compte, "lever", {"sanction": sanction.pk, "motif": "Fin"}, "lever"
    )
    assert dc.valider(d, par=bnc["pres"].compte).etat == Etat.VALIDEE
    assert pres_mandat.membre == bnc["pres"]
