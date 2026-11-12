import datetime

import pytest

from apps.cotisations.models import EtatVersement, MoisCotise, NiveauPart, Tarif
from apps.cotisations.regles import situation
from apps.cotisations.services import (
    CotisationRefusee,
    annuler,
    marquer_part_recue,
    rappeler_en_attente,
    refuser,
    regler,
    saisir_collecte,
    saisir_versement,
    valider,
)
from apps.cotisations.tests.conftest import enregistre_le
from apps.journal import models as j
from apps.journal.models import EntreeJournal
from apps.notifications.models import Notification

D = datetime.date
AUJ = D(2026, 3, 15)


def M(a, m):
    return D(a, m, 1)


@pytest.fixture(autouse=True)
def date_fixe(monkeypatch):
    import apps.cotisations.services as s

    monkeypatch.setattr(s, "aujourdhui", lambda: AUJ)


@pytest.fixture
def ancien(monde, depart):
    return enregistre_le(monde["m1"], D(2025, 1, 1))


def _mois(v):
    return sorted(v.mois.values_list("mois", flat=True))


def test_saisie_repartie_sur_mois_les_plus_anciens(ancien, compte_technique):
    v = saisir_versement(ancien, montant=300, date_versement=AUJ, par=compte_technique)
    assert v.etat == EtatVersement.EN_ATTENTE and v.paroisse == ancien.affectation_actuelle.paroisse
    assert _mois(v) == [M(2026, 1), M(2026, 2), M(2026, 3)]
    v2 = saisir_versement(ancien, montant=100, date_versement=AUJ, par=compte_technique)
    assert _mois(v2) == [M(2026, 4)]  # payé d'avance


def test_paiement_d_avance_limite_a_l_annee(ancien, compte_technique):
    with pytest.raises(CotisationRefusee):
        saisir_versement(ancien, montant=1300, date_versement=AUJ, par=compte_technique)
    v = saisir_versement(ancien, montant=1200, date_versement=AUJ, par=compte_technique)
    assert _mois(v)[-1] == M(2026, 12)


@pytest.mark.parametrize("montant", [150, 0, -100])
def test_montant_non_multiple_refuse(ancien, compte_technique, montant):
    with pytest.raises(CotisationRefusee):
        saisir_versement(ancien, montant=montant, date_versement=AUJ, par=compte_technique)
    assert not MoisCotise.objects.exists()


def test_saisie_fermee_sans_mois_de_depart(monde, compte_technique):
    with pytest.raises(CotisationRefusee, match="mois de départ"):
        saisir_versement(monde["m1"], montant=100, date_versement=AUJ, par=compte_technique)


def test_mois_choisis_et_mois_deja_paye_refuse(ancien, compte_technique):
    saisir_versement(
        ancien, montant=100, date_versement=AUJ, par=compte_technique, mois=[M(2026, 2)]
    )
    with pytest.raises(CotisationRefusee, match="déjà"):
        saisir_versement(
            ancien, montant=100, date_versement=AUJ, par=compte_technique, mois=[M(2026, 2)]
        )
    with pytest.raises(CotisationRefusee):
        saisir_versement(
            ancien, montant=100, date_versement=AUJ, par=compte_technique, mois=[M(2025, 12)]
        )


def test_collecte_tout_ou_rien(monde, depart, compte_technique):
    a = enregistre_le(monde["m1"], D(2025, 1, 1))
    autre_paroisse = enregistre_le(monde["m2"], D(2025, 1, 1))  # paroisse P2
    with pytest.raises(CotisationRefusee):
        saisir_collecte(
            monde["P1"],
            coches={a.pk: [M(2026, 1)], autre_paroisse.pk: [M(2026, 1)]},
            date_versement=AUJ,
            par=compte_technique,
        )
    assert not MoisCotise.objects.exists()
    faits = saisir_collecte(
        monde["P1"],
        coches={a.pk: [M(2026, 1), M(2026, 2)]},
        date_versement=AUJ,
        par=compte_technique,
    )
    assert len(faits) == 1 and faits[0].montant == 200


def test_validation_numero_recu_et_parts(
    ancien, monde, compte_technique, django_capture_on_commit_callbacks
):
    v = saisir_versement(ancien, montant=300, date_versement=AUJ, par=compte_technique)
    with django_capture_on_commit_callbacks(execute=True):
        (v,) = valider([v], par=compte_technique)
    assert v.etat == EtatVersement.VALIDE and v.numero_recu == "R2026-000001"
    assert v.parts == {"paroisse": 90, "circuit": 60, "region": 60, "national": 90}
    assert situation(ancien, M(2026, 3)).a_jour
    assert Notification.objects.filter(destinataire=ancien.compte).exists()
    v2 = saisir_versement(ancien, montant=100, date_versement=AUJ, par=compte_technique)
    assert valider([v2], par=compte_technique)[0].numero_recu == "R2026-000002"
    with pytest.raises(CotisationRefusee):
        valider([v2], par=compte_technique)  # déjà validé


def test_parts_avec_arrondi_total_exact(ancien, compte_technique):
    Tarif.objects.create(
        date_effet=M(2026, 1),
        montant=150,
        part_paroisse=33,
        part_circuit=33,
        part_region=17,
        part_national=17,
    )
    v = saisir_versement(ancien, montant=150, date_versement=AUJ, par=compte_technique)
    (v,) = valider([v], par=compte_technique)
    assert sum(v.parts.values()) == 150


def test_refus_libere_les_mois_et_notifie(
    ancien, monde, compte_technique, django_capture_on_commit_callbacks
):
    v = saisir_versement(ancien, montant=100, date_versement=AUJ, par=compte_technique)
    with pytest.raises(CotisationRefusee, match="motif"):
        refuser(v, motif=" ", par=compte_technique)
    with django_capture_on_commit_callbacks(execute=True):
        refuser(v, motif="Montant non reçu", par=compte_technique)
    v.refresh_from_db()
    assert v.etat == EtatVersement.REFUSE and not v.mois.filter(actif=True).exists()
    assert Notification.objects.filter(destinataire=monde["sec_p1"].compte).exists()
    # le mois redevient payable
    saisir_versement(ancien, montant=100, date_versement=AUJ, par=compte_technique)


def test_annulation_apres_validation(ancien, compte_technique):
    v = saisir_versement(ancien, montant=100, date_versement=AUJ, par=compte_technique)
    valider([v], par=compte_technique)
    annuler(v, motif="Erreur de membre", par=compte_technique)
    v.refresh_from_db()
    assert v.etat == EtatVersement.ANNULE and v.numero_recu  # le numéro reste (trace)
    assert situation(ancien, M(2026, 1)).retard == 1


def test_part_recue_montant_et_unicite(ancien, monde, compte_technique):
    v = saisir_versement(ancien, montant=300, date_versement=AUJ, par=compte_technique)
    (v,) = valider([v], par=compte_technique)
    mois_val = v.date_validation.date().replace(day=1)
    p = marquer_part_recue(
        niveau=NiveauPart.CIRCUIT,
        paroisse=monde["P1"],
        mois_validation=mois_val,
        par=compte_technique,
    )
    assert p.montant == 60
    with pytest.raises(CotisationRefusee):
        marquer_part_recue(
            niveau=NiveauPart.CIRCUIT,
            paroisse=monde["P1"],
            mois_validation=mois_val,
            par=compte_technique,
        )
    with pytest.raises(CotisationRefusee):  # rien à recevoir
        marquer_part_recue(
            niveau=NiveauPart.REGION,
            paroisse=monde["P2"],
            mois_validation=mois_val,
            par=compte_technique,
        )


def test_rappel_30_jours(ancien, monde, compte_technique, django_capture_on_commit_callbacks):
    from django.utils import timezone

    from apps.cotisations.models import Versement

    v = saisir_versement(ancien, montant=100, date_versement=AUJ, par=compte_technique)
    assert rappeler_en_attente(timezone.now().date()) == 0
    Versement.objects.filter(pk=v.pk).update(
        date_saisie=timezone.now() - datetime.timedelta(days=31)
    )
    with django_capture_on_commit_callbacks(execute=True):
        assert rappeler_en_attente(timezone.now().date()) == 1
    assert Notification.objects.filter(destinataire=monde["chef"].compte).exists()


def test_reglages(db, compte_technique):
    regler(mois_depart=D(2027, 1, 15), par=compte_technique)
    from apps.cotisations.models import ParametresCotisations

    assert ParametresCotisations.courant().mois_depart == D(2027, 1, 1)
    with pytest.raises(CotisationRefusee):
        regler(
            tarif={
                "date_effet": D(2027, 2, 1),
                "montant": 100,
                "part_paroisse": 30,
                "part_circuit": 20,
                "part_region": 20,
                "part_national": 20,
            },
            par=compte_technique,
        )


def test_tresorier_a_acces_cotisations_seulement(monde):
    from apps.bureaux.perimetre import Unite, unites_cotisations, unites_gerees

    tresorier = monde["tresorier"].compte
    assert Unite("paroisse", monde["P1"]) in unites_cotisations(tresorier)
    assert unites_gerees(tresorier) == []
    assert Unite("paroisse", monde["P1"]) in unites_cotisations(monde["sec_p1"].compte)
    assert unites_cotisations(monde["m1"].compte) == []


def test_journal_phrases_cotisations(ancien, compte_technique):
    from apps.journal.lecture import lire

    v = saisir_versement(ancien, montant=300, date_versement=AUJ, par=compte_technique)
    valider([v], par=compte_technique)
    lignes = lire(EntreeJournal.objects.filter(action__startswith="versement").order_by("date"))
    assert lignes[0].texte == (
        f"A enregistré un versement de 300 F pour {ancien.nom_complet} ({ancien.matricule}) "
        "(janvier à mars 2026)."
    )
    assert lignes[1].texte.startswith("A validé le versement de 300 F de")
    assert "R2026-000001" in lignes[1].texte
    assert EntreeJournal.objects.filter(action=j.VERSEMENT_SAISI).exists()
