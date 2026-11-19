"""« Ma page » en tuiles (style coloré, décision du 19/11/2026)."""

import datetime

from django.utils import timezone


def _page(client, compte):
    client.force_login(compte)
    return client.get("/").content.decode()


def test_membre_simple_voit_cotisations_et_evenement(client, monde, compte_technique):
    from apps.comptes.tableau import tuiles
    from apps.evenements.services import convoquer, creer_evenement

    m1 = monde["m1"]
    ev = creer_evenement(
        nom="Pèlerinage de la Nativité",
        lieu="Porto-Novo",
        debut=timezone.now() + datetime.timedelta(days=20),
        par=compte_technique,
    )
    convoquer(ev, membres=[m1], par=compte_technique)
    libelles = {t["libelle"]: t for t in tuiles(m1.compte)}
    assert "Mes cotisations" in libelles and "Prochain événement" in libelles
    assert "Pèlerinage de la Nativité" in libelles["Prochain événement"]["valeur"]
    assert "Décisions à prendre" not in libelles  # pas BN
    page = _page(client, m1.compte)
    assert 'class="tuiles"' in page and "Pèlerinage de la Nativité" in page


def test_bn_voit_les_decisions(monde, client_technique, compte_technique):
    from apps.comptes.tableau import tuiles

    libelles = [t["libelle"] for t in tuiles(compte_technique)]
    assert "Décisions à prendre" in libelles
    assert "Mes cotisations" not in libelles  # compte technique : pas membre


def test_pas_d_evenement_annule_ni_passe(monde, compte_technique):
    from apps.comptes.tableau import tuiles
    from apps.evenements.services import annuler_evenement, convoquer, creer_evenement

    m1 = monde["m1"]
    ev = creer_evenement(
        nom="Annulé", lieu="X", debut=timezone.now() + datetime.timedelta(days=5),
        par=compte_technique,
    )
    convoquer(ev, membres=[m1], par=compte_technique)
    annuler_evenement(ev, motif="Pluie", par=compte_technique)
    libelles = {t["libelle"]: t for t in tuiles(m1.compte)}
    assert "Prochain événement" not in libelles
