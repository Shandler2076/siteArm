"""Animations (décision du 19/11/2026) : sobres, sans bibliothèque, coupées si le téléphone
demande de « réduire les animations »."""

from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]


def test_reglage_reduire_les_animations_respecte():
    css = (RACINE / "static/css/site.css").read_text(encoding="utf-8")
    bloc = css[css.index("@media (prefers-reduced-motion: reduce)") :]
    assert "animation: none !important" in bloc and "transition: none !important" in bloc
    js = (RACINE / "static/js/site.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in js  # compteurs et diaporama immobiles


@pytest.mark.django_db
def test_diaporama_de_l_accueil(client, territoire):
    html = client.get("/").content.decode()
    debut = html.index('class="diaporama"')
    bloc = html[debut : html.index("</figure>", debut)]
    assert bloc.count("<img") == 4 and "diaporama__points" in bloc


def test_tuile_courriers_a_signer_attire_l_attention(client, monde, donner_mandat):
    from apps.bureaux.perimetre import Unite
    from apps.courrier import services as s

    pres, sn = monde["m1"], monde["m2"]
    donner_mandat(pres, "Président")
    donner_mandat(sn, "Secrétaire national")
    s.preparer(
        unite=Unite("national", None),
        nature="lettre",
        objet="Essai",
        texte="Texte",
        bureaux=[f"paroisse-{monde['P1'].pk}"],
        par=sn.compte,
    )
    client.force_login(pres.compte)
    assert "tuile--attention" in client.get("/").content.decode()
