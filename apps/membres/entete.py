"""En-tête commun de l'Église pour tous les documents produits (décision du 20/11/2026).

Le modèle est celui de la fiche d'identification :
- un bandeau bleu marine, avec le logo de la Congrégation (sans texte en courbe) à gauche et
  celui de l'Armée du Salut à droite, sur fond blanc ; entre les deux, les marques de l'Église :
  la Congrégation, le Comité National de Coordination, le Bureau National de Commandement ;
- un filet rouge sous le bandeau ;
- dessous : « ARMÉE DU SALUT DU BÉNIN », le titre du document, la devise.

Les courriers gardent leur modèle national, et l'autorisation sa carte (décisions précédentes).
Le même contenu existe pour les classeurs Excel (`entete_excel`).
"""

import io

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from apps.membres.pdf import (
    GRIS,
    LOGO_AS,
    LOGO_CONGREGATION_SANS_TEXTE,
    MARINE,
    OR,
    ROUGE,
    _polices,
    taille_pour_largeur,
)

CONGREGATION = (
    "CONGRÉGATION CHRÉTIENNE DE L'ORDRE SACRÉ ÉTERNEL",
    "DES CHÉRUBINS ET SÉRAPHINS « MONT SION » DU BÉNIN",
)
COMITE = "COMITÉ NATIONAL DE COORDINATION"
BUREAU = "BUREAU NATIONAL DE COMMANDEMENT"
MARQUES = (" ".join(CONGREGATION), COMITE, BUREAU)
MOUVEMENT = "ARMÉE DU SALUT DU BÉNIN"
DEVISE = "« FOI – AMOUR – JUSTICE »"

HAUTEUR_FICHE = 48 * mm  # la fiche d'identification (grand modèle)


def bandeau_eglise(c, larg: float, haut: float, *, hauteur: float, marge: float) -> float:
    """Bandeau aux deux logos et aux marques de l'Église, sur toute la largeur de la page.
    Les mesures sont celles de la fiche (48 mm) mises à l'échelle. Renvoie le bas du filet."""
    _polices()
    k = hauteur / HAUTEUR_FICHE
    police = 0.3 + 0.7 * k  # les textes rétrécissent moins vite que le bandeau
    c.saveState()
    c.setFillColor(MARINE)
    c.rect(0, haut - hauteur, larg, hauteur, stroke=0, fill=1)
    c.setFillColor(ROUGE)
    c.rect(0, haut - hauteur - 2 * k * mm, larg, 2 * k * mm, stroke=0, fill=1)
    # Logo de l'Église à gauche, logo de l'Armée du Salut à droite, sur fond blanc.
    c.setFillColor(colors.white)
    c.roundRect(
        marge - 2 * k * mm,
        haut - 44 * k * mm,
        48 * k * mm,
        40 * k * mm,
        4 * k * mm,
        stroke=0,
        fill=1,
    )
    if LOGO_CONGREGATION_SANS_TEXTE.exists():
        c.drawImage(
            ImageReader(str(LOGO_CONGREGATION_SANS_TEXTE)),
            marge - 1 * k * mm,
            haut - 41 * k * mm,
            46 * k * mm,
            34.5 * k * mm,
            mask="auto",
            preserveAspectRatio=True,
        )
    c.roundRect(
        larg - marge - 38 * k * mm,
        haut - 44 * k * mm,
        40 * k * mm,
        40 * k * mm,
        4 * k * mm,
        stroke=0,
        fill=1,
    )
    if LOGO_AS.exists():
        c.drawImage(
            ImageReader(str(LOGO_AS)),
            larg - marge - 36 * k * mm,
            haut - 42 * k * mm,
            36 * k * mm,
            36 * k * mm,
            mask="auto",
            preserveAspectRatio=True,
        )
    # Entre les deux logos : la Congrégation, le Comité, le Bureau National de Commandement.
    gauche, droite = marge + 49 * k * mm, larg - marge - 41 * k * mm
    centre, utile = (gauche + droite) / 2, droite - gauche
    for texte, couleur, taille, y in (
        (CONGREGATION[0], colors.white, 8.5, 12),
        (CONGREGATION[1], colors.white, 8.5, 16.5),
        (COMITE, OR, 10.5, 27),
        (BUREAU, colors.white, 12.5, 35.5),
    ):
        t = taille_pour_largeur(texte, "Sans-Gras", taille * police, utile, taille_min=4)
        c.setFillColor(couleur)
        c.setFont("Sans-Gras", t)
        c.drawCentredString(centre, haut - y * k * mm, texte)
    c.setStrokeColor(OR)
    c.setLineWidth(0.8 * police)
    demi = min(22 * k * mm, utile / 2)
    c.line(centre - demi, haut - 21 * k * mm, centre + demi, haut - 21 * k * mm)
    c.restoreState()
    return haut - hauteur - 2 * k * mm


def titre_sous_bandeau(c, larg: float, y: float, titre: str, *, hauteur: float, marge: float):
    """« ARMÉE DU SALUT DU BÉNIN », le titre du document (en majuscules), la devise.
    Renvoie la hauteur sous la devise."""
    k = hauteur / HAUTEUR_FICHE
    f = 0.55 + 0.45 * k
    utile = larg - 2 * marge
    centre = larg / 2
    c.saveState()
    c.setFillColor(MARINE)
    t = taille_pour_largeur(MOUVEMENT, "Sans-Gras", 14 * f, utile, taille_min=6)
    c.setFont("Sans-Gras", t)
    c.drawCentredString(centre, y - 8 * f * mm, MOUVEMENT)
    c.setFillColor(ROUGE)
    titre = titre.upper()
    t = taille_pour_largeur(titre, "Sans-Gras", 12.5 * f, utile, taille_min=6)
    from apps.membres.pdf import _ajuste

    c.setFont("Sans-Gras", t)
    c.drawCentredString(centre, y - 14.5 * f * mm, _ajuste(titre, "Sans-Gras", t, utile))
    c.setFillColor(GRIS)
    c.setFont("Sans", 9.5 * f)
    c.drawCentredString(centre, y - 20 * f * mm, DEVISE)
    c.restoreState()
    return y - 23 * f * mm


def entete_eglise(c, larg: float, haut: float, titre: str, *, hauteur: float, marge: float):
    """Bandeau + titre : l'en-tête complet. Renvoie la hauteur disponible dessous."""
    y = bandeau_eglise(c, larg, haut, hauteur=hauteur, marge=marge)
    return titre_sous_bandeau(c, larg, y, titre, hauteur=hauteur, marge=marge)


# --- Excel -------------------------------------------------------------------------------------


def _logo_excel(chemin, hauteur_px: int):
    from openpyxl.drawing.image import Image as ImageExcel
    from PIL import Image

    with Image.open(chemin, formats=["PNG"]) as im:
        im = im.convert("RGBA")
        largeur_px = round(im.width * hauteur_px / im.height)
        im = im.resize((largeur_px, hauteur_px))
        tampon = io.BytesIO()
        im.save(tampon, "PNG")
    tampon.seek(0)
    return ImageExcel(tampon)


def entete_excel(ws, titre: str, lignes: list[str], nb_colonnes: int) -> int:
    """En-tête commun en haut d'une feuille Excel. Renvoie la première ligne libre.

    Bandeau bleu (lignes 1 à 4) : logo de la Congrégation dans la première colonne, logo de
    l'Armée du Salut dans la dernière, les marques de l'Église au milieu ; puis le mouvement,
    le titre du document et la devise ; puis les lignes d'information."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    largeur = max(nb_colonnes, 6)
    fin = get_column_letter(largeur)
    avant_fin = get_column_letter(largeur - 1)
    fond = PatternFill("solid", fgColor="14284B")
    centre = Alignment(horizontal="center", vertical="center")

    def ecrire(rangee, debut, derniere, texte, police):
        ws.merge_cells(f"{debut}{rangee}:{derniere}{rangee}")
        cellule = ws[f"{debut}{rangee}"]
        cellule.value = texte
        cellule.data_type = "s"
        cellule.font = police
        cellule.alignment = centre

    bandeau = [
        (CONGREGATION[0], Font(bold=True, size=9, color="FFFFFF"), 15),
        (CONGREGATION[1], Font(bold=True, size=9, color="FFFFFF"), 15),
        (COMITE, Font(bold=True, size=11, color="D4A017"), 17),
        (BUREAU, Font(bold=True, size=12, color="FFFFFF"), 19),
    ]
    for n, (texte, police, hauteur) in enumerate(bandeau, start=1):
        ecrire(n, "B", avant_fin, texte, police)
        ws.row_dimensions[n].height = hauteur
        for col in range(1, largeur + 1):
            ws.cell(row=n, column=col).fill = fond
    sous = [
        (MOUVEMENT, Font(bold=True, size=13, color="14284B"), 22),
        (titre.upper(), Font(bold=True, size=12, color="B3122E"), 18),
        (DEVISE, Font(italic=True, size=9, color="5B6578"), 15),
    ]
    for n, (texte, police, hauteur) in enumerate(sous, start=len(bandeau) + 1):
        ecrire(n, "A", fin, texte, police)
        ws.row_dimensions[n].height = hauteur
    # Les logos : première et dernière colonnes, assez larges pour eux.
    for lettre, minimum in (("A", 18), (fin, 11)):
        if (ws.column_dimensions[lettre].width or 0) < minimum:
            ws.column_dimensions[lettre].width = minimum
    # Assez de place au milieu pour les marques de l'Église (les colonnes ne font que s'élargir).
    milieu = [get_column_letter(i) for i in range(2, largeur)]
    total = sum(ws.column_dimensions[x].width or 8.43 for x in milieu)
    if total < 58:
        ajout = (58 - total) / len(milieu)
        for x in milieu:
            ws.column_dimensions[x].width = (ws.column_dimensions[x].width or 8.43) + ajout
    for chemin, ancre in ((LOGO_CONGREGATION_SANS_TEXTE, "A1"), (LOGO_AS, f"{fin}1")):
        if chemin.exists():
            ws.add_image(_logo_excel(chemin, 76), ancre)
    # Impression : toute la largeur sur une page (paysage si le tableau est large).
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    if nb_colonnes > 6:
        ws.page_setup.orientation = "landscape"
    n = len(bandeau) + len(sous) + 1
    for texte in lignes:
        cellule = ws.cell(row=n, column=1, value=texte)
        cellule.data_type = "s"
        n += 1
    return n + 1  # une ligne vide avant le tableau
