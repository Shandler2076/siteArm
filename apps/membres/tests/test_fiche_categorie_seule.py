# ruff: noqa: F811  (fixtures importées puis demandées en paramètres)
"""Fiche (remarque du 20/11/2026) : « Catégorie » seule ; la ligne « Statut » n'apparaît que si
le membre n'est plus actif (sanctionné, exclu, démissionnaire, décédé)."""

from html import unescape

from apps.bureaux.tests.conftest import (  # noqa: F401
    compte_technique,
    donner_mandat,
    monde,
    nouveau_membre,
    territoire,
)


def _pages(client, monde, m, compte_technique):
    client.force_login(m.compte)
    yield unescape(client.get("/membres/ma-fiche/").content.decode())
    client.force_login(monde["sec_p1"].compte)
    yield unescape(
        client.get(f"/bureau/paroisse-{monde['P1'].pk}/membres/{m.matricule}/").content.decode()
    )
    client.force_login(compte_technique)
    yield unescape(client.get(f"/membres/bn/{m.matricule}/").content.decode())


def test_membre_actif_sans_ligne_statut(client, monde, compte_technique):
    for page in _pages(client, monde, monde["m1"], compte_technique):
        assert "<dt>Catégorie</dt>" in page and "<dt>Statut</dt>" not in page


def test_membre_sanctionne_garde_la_ligne_statut(client, monde, compte_technique):
    import datetime

    from apps.mouvements.statuts import changer_statut

    m1 = monde["m1"]
    changer_statut(
        m1, "sanctionne", par=compte_technique, date_effet=datetime.date.today(), motif="test"
    )
    m1.refresh_from_db()
    pages = list(_pages(client, monde, m1, compte_technique))
    for page in pages[1:]:  # le bureau et le BNC le voient
        assert "<dt>Statut</dt>" in page and "Sanctionné" in page
