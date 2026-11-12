"""Corrections de la relecture finale (module 2, étape 2)."""

import datetime
from html import unescape

import pytest
from django.test import Client

from apps.cotisations.models import NiveauPart
from apps.cotisations.services import (
    CotisationRefusee,
    marquer_part_recue,
    saisir_versement,
    valider,
)
from apps.cotisations.tests.conftest import enregistre_le
from apps.mouvements.models import HistoriqueMembre, TypeHistorique

D = datetime.date


@pytest.fixture(autouse=True)
def date_fixe(monkeypatch):
    import apps.cotisations.services as s
    import apps.cotisations.views as v

    monkeypatch.setattr(s, "aujourdhui", lambda: D(2026, 3, 15))
    monkeypatch.setattr(v, "aujourdhui", lambda: D(2026, 3, 15))


@pytest.fixture
def prets(monde, depart):
    for k in ("m1", "m2", "sec_p1", "tresorier"):
        enregistre_le(monde[k], D(2025, 1, 1))
    return monde


def _deces(m, jour):
    from apps.membres.models import Membre

    HistoriqueMembre.objects.create(
        membre=m,
        type=TypeHistorique.STATUT,
        ancien="actif",
        nouveau="decede",
        date_effet=jour,
        motif="Test",
    )
    Membre.objects.filter(pk=m.pk).update(statut="decede")
    m.refresh_from_db()


def test_pas_de_paiement_apres_le_deces(prets, compte_technique):
    m = prets["m1"]
    _deces(m, D(2026, 2, 10))
    with pytest.raises(CotisationRefusee):
        saisir_versement(m, montant=1000, date_versement=D(2026, 3, 1), par=compte_technique)
    v = saisir_versement(m, montant=200, date_versement=D(2026, 3, 1), par=compte_technique)
    assert sorted(v.mois.values_list("mois", flat=True)) == [D(2026, 1, 1), D(2026, 2, 1)]
    with pytest.raises(CotisationRefusee):
        saisir_versement(
            m, montant=100, date_versement=D(2026, 3, 1), par=compte_technique, mois=[D(2026, 4, 1)]
        )


def test_mois_d_exclusion_non_payable(prets, compte_technique):
    m = prets["m1"]
    for date_effet, ancien, nouveau in [
        (D(2026, 1, 20), "actif", "exclu"),
        (D(2026, 2, 10), "exclu", "actif"),
    ]:
        HistoriqueMembre.objects.create(
            membre=m,
            type=TypeHistorique.STATUT,
            ancien=ancien,
            nouveau=nouveau,
            date_effet=date_effet,
            motif="Test",
        )
    with pytest.raises(CotisationRefusee):
        saisir_versement(
            m, montant=100, date_versement=D(2026, 3, 1), par=compte_technique, mois=[D(2026, 2, 1)]
        )


def test_grille_sans_case_apres_le_deces(prets):
    _deces(prets["m1"], D(2026, 2, 10))
    c = Client()
    c.force_login(prets["sec_p1"].compte)
    html = c.get(f"/cotisations/paroisse-{prets['P1'].pk}/grille/").content.decode()
    assert f'name="c-{prets["m1"].pk}" value="2026-04-01"' not in html
    assert f'name="c-{prets["sec_p1"].pk}" value="2026-04-01"' in html


def test_part_du_mois_en_cours_non_marquable(prets, compte_technique):
    v = saisir_versement(
        prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=compte_technique
    )
    (v,) = valider([v], par=prets["chef"].compte)
    mois = v.date_validation.date().replace(day=1)
    with pytest.raises(CotisationRefusee, match="mois terminé"):
        marquer_part_recue(
            niveau=NiveauPart.CIRCUIT,
            paroisse=prets["P1"],
            mois_validation=mois,
            par=compte_technique,
            aujourd_hui=mois,
        )


def test_pas_de_validation_par_celui_qui_a_saisi(prets):
    compte = prets["chef"].compte
    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=compte)
    with pytest.raises(CotisationRefusee, match="autre membre"):
        valider([v], par=compte)


def test_liens_etat_et_recus_pour_le_bureau(prets):
    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    (v,) = valider([v], par=None)
    c = Client()
    c.force_login(prets["tresorier"].compte)
    html = unescape(c.get(f"/cotisations/paroisse-{prets['P1'].pk}/grille/").content.decode())
    assert f"/cotisations/membre/{prets['m1'].matricule}/etat.pdf" in html
    assert f"/cotisations/recu/{v.pk}.pdf" in html and v.numero_recu in html


def test_entrees_invalides_sans_erreur_500(prets):
    c = Client()
    c.force_login(prets["sec_p1"].compte)
    assert c.get(f"/cotisations/paroisse-{prets['P1'].pk}/grille/?annee=0").status_code == 200
    assert c.get(f"/cotisations/paroisse-{prets['P1'].pk}/grille/?annee=99999").status_code == 200
    c.force_login(prets["chef"].compte)
    r = c.post(
        f"/cotisations/circuit-{prets['Ekpe A'].pk}/parts/", {"paroisse": "abc", "mois": "x"}
    )
    assert r.status_code == 404


def test_recu_date_locale(prets):
    import io

    from django.utils import timezone
    from pypdf import PdfReader

    from apps.cotisations.models import Versement
    from apps.cotisations.pdf import recu_pdf

    v = saisir_versement(prets["m1"], montant=100, date_versement=D(2026, 3, 1), par=None)
    (v,) = valider([v], par=None)
    # 31/12/2026 23:30 UTC = 01/01/2027 00:30 à Porto-Novo (UTC+1)
    Versement.objects.filter(pk=v.pk).update(
        date_validation=datetime.datetime(2026, 12, 31, 23, 30, tzinfo=datetime.UTC)
    )
    v.refresh_from_db()
    texte = PdfReader(io.BytesIO(recu_pdf(v))).pages[0].extract_text()
    assert timezone.localtime(v.date_validation).strftime("%d/%m/%Y") in texte


def test_journal_reglages_lisible(db, compte_technique):
    from apps.cotisations.services import regler
    from apps.journal.lecture import lire
    from apps.journal.models import EntreeJournal

    regler(par=compte_technique, mois_depart=D(2027, 1, 1))
    (ligne,) = lire(EntreeJournal.objects.filter(action="reglage_cotisations"))
    assert "janvier 2027" in ligne.texte
