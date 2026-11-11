"""Corrections de la relecture finale de l'étape 6."""

import re
from datetime import date
from unittest import mock

import pytest

from apps.mouvements import services
from apps.mouvements.models import AvisMutation
from apps.mouvements.services import (
    blocage_rehabilitation,
    decider_mutation,
    decider_signalement,
    demander_mutation,
    signaler,
)
from apps.mouvements.statuts import changer_statut


@pytest.fixture
def mutation(monde, compte_technique):
    return demander_mutation(membre=monde["m1"], paroisse_arrivee=monde["P4"], par=compte_technique)


def test_lien_du_membre_mute_mene_a_sa_fiche(client, monde, mutation):
    client.force_login(monde["m1"].compte)
    r = client.get(f"/bureau/mutations/{mutation.pk}/")
    assert r.status_code == 302 and r.url == "/membres/ma-fiche/"


def test_bn_ne_donne_pas_l_avis_du_circuit(client_technique, monde, mutation):
    cle = f"circuit-{monde['Ekpe A'].pk}"
    page = client_technique.get(f"/bureau/{cle}/mutations/{mutation.pk}/").content.decode()
    assert 'name="favorable"' not in page
    r = client_technique.post(f"/bureau/{cle}/mutations/{mutation.pk}/avis/", {"favorable": "1"})
    assert r.status_code == 404 and not AvisMutation.objects.exists()


def test_decisions_verrouillent_le_membre(monde, mutation, compte_technique):
    sig = signaler(
        membre=monde["m2"],
        type="deces",
        par=compte_technique,
        unite="national",
        date_effet=date(2026, 11, 1),
    )
    with mock.patch.object(
        services, "_verrouiller_membre", wraps=services._verrouiller_membre
    ) as v:
        decider_mutation(mutation=mutation, valider=True, par=compte_technique)
        decider_signalement(signalement=sig, confirmer=True, par=compte_technique)
    assert [c.args[0] for c in v.call_args_list] == [monde["m1"].pk, monde["m2"].pk]


def _formulaires(html):
    return re.findall(r"<form.*?</form>", html, flags=re.S)


def test_entree_dans_le_motif_ne_confirme_pas(client_technique, monde, compte_technique, mutation):
    sig = signaler(
        membre=monde["m2"],
        type="deces",
        par=compte_technique,
        unite="national",
        date_effet=date(2026, 11, 1),
    )
    for url, champ in (
        (f"/bureau/bn/signalements/{sig.pk}/", "motif_refus"),
        (f"/bureau/bn/mutations/{mutation.pk}/", "commentaire"),
    ):
        html = client_technique.get(url).content.decode()
        for form in _formulaires(html):
            if f'name="{champ}"' in form:
                premier = re.search(r'<button[^>]*value="(\w+)"', form).group(1)
                assert premier == "refuser", url


def test_fin_d_exclusion_temporaire_n_est_pas_une_rehabilitation(monde):
    m1 = monde["m1"]
    changer_statut(m1, "exclu", par=None, date_effet=date(2023, 1, 1), motif="Exclusion temporaire")
    changer_statut(m1, "actif", par=None, date_effet=date(2023, 6, 1), motif="Fin de la sanction")
    changer_statut(m1, "exclu", par=None, date_effet=date(2025, 1, 1), motif="Exclusion")
    assert blocage_rehabilitation(m1, date(2026, 11, 11)) is None


def test_rehabilitation_reelle_puis_exclusion_bloque(monde, compte_technique):
    m1 = monde["m1"]
    changer_statut(m1, "exclu", par=None, date_effet=date(2023, 1, 1), motif="Exclusion")
    sig = signaler(
        membre=m1,
        type="rehabilitation",
        par=compte_technique,
        unite="national",
        reference="Engagement 1",
        jour=date(2024, 1, 1),
    )
    decider_signalement(
        signalement=sig, confirmer=True, par=compte_technique, jour=date(2024, 1, 1)
    )
    changer_statut(m1, "exclu", par=None, date_effet=date(2025, 1, 1), motif="Exclusion")
    assert "art. 172" in blocage_rehabilitation(m1, date(2026, 11, 11))
