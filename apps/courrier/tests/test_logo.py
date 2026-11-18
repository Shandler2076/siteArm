"""Nouveau logo de la Congrégation sans texte (décision du 18/11/2026)."""

from html import unescape


def test_logo_sans_texte_dans_l_en_tete_des_courriers_et_la_fiche():
    from apps.courrier import pdf as courrier_pdf
    from apps.membres import pdf as membres_pdf

    assert membres_pdf.LOGO_CONGREGATION_SANS_TEXTE.name == "logo-congregation-sans-texte.png"
    assert membres_pdf.LOGO_CONGREGATION_SANS_TEXTE.exists()
    assert courrier_pdf.LOGO_EN_TETE == membres_pdf.LOGO_CONGREGATION_SANS_TEXTE


def test_accueil_nom_de_la_congregation_sous_le_logo(client, db):
    html = unescape(client.get("/").content.decode())
    debut = html.index("logo-congregation-sans-texte")
    nom = html.index("Congrégation Chrétienne", debut)
    assert nom > debut
    assert "de l'Ordre Sacré Éternel" in html and "Mont-Sion du Bénin" in html
