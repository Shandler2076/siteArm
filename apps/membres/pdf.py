"""Fiche d'identification d'un membre au format PDF (A4)."""

import io
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from apps.membres.models import Membre

MARINE = colors.HexColor("#14284B")
ROUGE = colors.HexColor("#B3122E")
OR = colors.HexColor("#D4A017")
GRIS = colors.HexColor("#5B6578")
FOND = colors.HexColor("#F4F6FA")

STATIQUE = Path(settings.BASE_DIR) / "static"
LOGO_AS = STATIQUE / "img" / "logo-armee-du-salut.png"
LOGO_CONGREGATION = STATIQUE / "img" / "logo-congregation-pdf.png"
# Nouveau logo sans texte (18/11/2026) : là où le nom de la Congrégation est déjà écrit
# (courriers, fiche du membre).
LOGO_CONGREGATION_SANS_TEXTE = STATIQUE / "img" / "logo-congregation-sans-texte.png"

_polices_ok = False


_LOGOS_PALES: dict = {}


def _logo_pale(intensite: float = 0.10) -> ImageReader | None:
    """Logo de l'Armée du Salut éclairci (filigrane), préparé une seule fois par intensité."""
    if intensite not in _LOGOS_PALES and LOGO_AS.exists():
        from PIL import Image

        logo = Image.open(LOGO_AS, formats=["PNG"]).convert("RGBA")
        fond = Image.new("RGBA", logo.size, (255, 255, 255, 0))
        pale = Image.blend(fond, logo, intensite)
        tampon = io.BytesIO()
        pale.save(tampon, "PNG")
        tampon.seek(0)
        _LOGOS_PALES[intensite] = ImageReader(tampon)
    return _LOGOS_PALES.get(intensite)


def filigrane(
    c, x: float, y: float, largeur: float, hauteur: float, mot: str = "", intensite: float = 0.10
) -> None:
    """Fond de page (décision du 19/11/2026) : logo de l'Armée du Salut en filigrane. À dessiner
    AVANT le contenu. Le mot (« AUTORISÉ », « PAYÉ ») se pose ensuite par `mot_filigrane`."""
    cote = min(largeur, hauteur) * 0.8
    logo = _logo_pale(intensite)
    if logo is not None:
        c.drawImage(
            logo,
            x + (largeur - cote) / 2,
            y + (hauteur - cote) / 2,
            cote,
            cote,
            mask="auto",
            preserveAspectRatio=True,
        )


def mot_filigrane(c, x: float, y: float, largeur: float, hauteur: float, mot: str) -> None:
    """Le mot en grand, en bleu, en biais, transparent : posé APRÈS le contenu, il se voit
    même sur la photo et le code QR, sans gêner la lecture."""
    import math

    _polices()
    angle = math.degrees(math.atan2(hauteur, largeur))
    diagonale = math.hypot(largeur, hauteur)
    largeur_unite = pdfmetrics.stringWidth(mot, "Sans-Gras", 1)
    taille = min(diagonale * 0.75 / largeur_unite, min(largeur, hauteur) * 0.35)
    c.saveState()
    c.setFillColor(colors.Color(0.08, 0.16, 0.29, alpha=0.12))  # marine #14284B, transparent
    c.setFont("Sans-Gras", taille)
    c.translate(x + largeur / 2, y + hauteur / 2)
    c.rotate(angle)
    c.drawCentredString(0, -taille / 3, mot)
    c.restoreState()


def _polices():
    global _polices_ok
    if not _polices_ok:
        polices = STATIQUE / "fonts"
        pdfmetrics.registerFont(TTFont("Sans", str(polices / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("Sans-Gras", str(polices / "DejaVuSans-Bold.ttf")))
        _polices_ok = True


def taille_pour_largeur(
    texte: str, police: str, taille_max: float, largeur_max: float, taille_min: float = 9
) -> float:
    """Plus grande taille de police (≤ taille_max, ≥ taille_min) qui fait tenir le texte."""
    taille = taille_max
    while taille > taille_min and pdfmetrics.stringWidth(texte, police, taille) > largeur_max:
        taille -= 0.5
    return taille


def _ajuste(texte: str, police: str, taille: float, largeur_max: float) -> str:
    """Coupe avec « … » si le texte dépasse encore à la taille minimale."""
    if pdfmetrics.stringWidth(texte, police, taille) <= largeur_max:
        return texte
    while texte and pdfmetrics.stringWidth(texte + "…", police, taille) > largeur_max:
        texte = texte[:-1]
    return texte.rstrip() + "…"


def _image_photo(membre: Membre):
    photo = membre.photo_acceptee
    if not photo:
        return None
    try:
        with photo.fichier.open("rb") as f:
            return ImageReader(io.BytesIO(f.read()))
    except OSError:
        return None  # fichier introuvable : « Photo à venir » plutôt qu'une erreur


def fiche_identification_pdf(membre: Membre, mot_de_passe: str | None = None) -> bytes:
    _polices()
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(f"Fiche d'identification — {membre.matricule}")
    c.setAuthor("Armée du Salut du Bénin")
    dessiner_fiche(c, membre, mot_de_passe)
    c.save()
    return tampon.getvalue()


def dessiner_fiche(c: canvas.Canvas, membre: Membre, mot_de_passe: str | None) -> None:
    """Dessine une fiche d'identification sur une page (pour un PDF d'une ou plusieurs fiches)."""
    _polices()
    larg, haut = A4
    marge = 18 * mm

    # En-tête : logos et titre
    c.setFillColor(MARINE)
    c.rect(0, haut - 48 * mm, larg, 48 * mm, stroke=0, fill=1)
    c.setFillColor(ROUGE)
    c.rect(0, haut - 50 * mm, larg, 2 * mm, stroke=0, fill=1)
    # Logo de l'Église à gauche, logo de l'Armée du Salut à droite.
    c.setFillColor(colors.white)
    c.roundRect(marge - 2 * mm, haut - 44 * mm, 48 * mm, 40 * mm, 4 * mm, stroke=0, fill=1)
    c.drawImage(
        ImageReader(str(LOGO_CONGREGATION_SANS_TEXTE)),
        marge - 1 * mm,
        haut - 41 * mm,
        46 * mm,
        34.5 * mm,
        mask="auto",
        preserveAspectRatio=True,
    )
    c.roundRect(larg - marge - 38 * mm, haut - 44 * mm, 40 * mm, 40 * mm, 4 * mm, stroke=0, fill=1)
    c.drawImage(
        ImageReader(str(LOGO_AS)),
        larg - marge - 36 * mm,
        haut - 42 * mm,
        36 * mm,
        36 * mm,
        mask="auto",
    )
    # Entre les deux logos, les marques de l'Église comme sur les courriers (20/11/2026) :
    # la Congrégation, le Comité National de Coordination, le Bureau National de Commandement.
    gauche, droite = marge + 49 * mm, larg - marge - 41 * mm
    centre, utile = (gauche + droite) / 2, droite - gauche
    for texte, couleur, taille, hauteur in (
        ("CONGRÉGATION CHRÉTIENNE DE L'ORDRE SACRÉ ÉTERNEL", colors.white, 8.5, 12),
        ("DES CHÉRUBINS ET SÉRAPHINS « MONT SION » DU BÉNIN", colors.white, 8.5, 16.5),
        ("COMITÉ NATIONAL DE COORDINATION", OR, 10.5, 27),
        ("BUREAU NATIONAL DE COMMANDEMENT", colors.white, 12.5, 35.5),
    ):
        taille = taille_pour_largeur(texte, "Sans-Gras", taille, utile, taille_min=6)
        c.setFillColor(couleur)
        c.setFont("Sans-Gras", taille)
        c.drawCentredString(centre, haut - hauteur * mm, texte)
    c.setStrokeColor(OR)
    c.setLineWidth(0.8)
    c.line(centre - 22 * mm, haut - 21 * mm, centre + 22 * mm, haut - 21 * mm)

    # Sous l'en-tête : le titre de la fiche et la devise.
    centre_page = larg / 2
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 14)
    c.drawCentredString(centre_page, haut - 58 * mm, "ARMÉE DU SALUT DU BÉNIN")
    c.setFillColor(ROUGE)
    c.setFont("Sans-Gras", 12.5)
    c.drawCentredString(centre_page, haut - 64.5 * mm, "FICHE D'IDENTIFICATION")
    c.setFillColor(GRIS)
    c.setFont("Sans", 9.5)
    c.drawCentredString(centre_page, haut - 70 * mm, "« FOI – AMOUR – JUSTICE »")

    # Matricule et photo
    y = haut - 83 * mm
    c.setFillColor(MARINE)
    c.roundRect(marge, y - 4 * mm, 92 * mm, 14 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Sans-Gras", 20)
    c.drawString(marge + 5 * mm, y, membre.matricule)
    c.setFillColor(MARINE)
    largeur_nom = larg - 2 * marge - 44 * mm  # jusqu'au cadre photo
    taille = taille_pour_largeur(membre.nom_complet, "Sans-Gras", 15, largeur_nom)
    c.setFont("Sans-Gras", taille)
    c.drawString(marge, y - 14 * mm, _ajuste(membre.nom_complet, "Sans-Gras", taille, largeur_nom))

    px, py, pl, ph = larg - marge - 38 * mm, haut - 125 * mm, 38 * mm, 48 * mm
    c.setStrokeColor(OR)
    c.setLineWidth(1.5)
    c.rect(px, py, pl, ph, stroke=1, fill=0)
    image = _image_photo(membre)
    if image:
        c.drawImage(image, px + 1, py + 1, pl - 2, ph - 2, preserveAspectRatio=True, anchor="c")
    else:
        c.setFillColor(GRIS)
        c.setFont("Sans", 9)
        c.drawCentredString(px + pl / 2, py + ph / 2, "Photo à venir")

    # Informations
    a = membre.affectation_actuelle
    naissance = membre.date_naissance.strftime("%d/%m/%Y") if membre.date_naissance else "—"
    region_int = membre.region_integration
    lignes = [
        ("Grade", membre.get_grade_display() if membre.grade is not None else "—"),
        ("Catégorie", membre.get_categorie_display()),
        ("Statut", membre.get_statut_display()),
        ("Sexe", membre.get_sexe_display()),
        ("Date de naissance", naissance),
        ("Lieu de naissance", membre.lieu_naissance or "—"),
        ("Téléphone", membre.telephone),
        ("Année d'intégration", str(membre.annee_integration)),
        ("Paroisse d'intégration", membre.paroisse_integration.nom),
        ("Région d'intégration", f"{region_int.code} — {region_int.nom}"),
        ("Paroisse actuelle", a.paroisse.nom if a else "—"),
        ("Circuit actuel", a.circuit_a_date.nom if a else "—"),
        ("Région actuelle", a.region_a_date.nom if a else "—"),
    ]
    y = haut - 131 * mm
    for i, (libelle, valeur) in enumerate(lignes):
        if i % 2 == 0:
            c.setFillColor(FOND)
            c.rect(marge, y - 2.5 * mm, larg - 2 * marge, 8 * mm, stroke=0, fill=1)
        c.setFillColor(GRIS)
        c.setFont("Sans", 9.5)
        c.drawString(marge + 3 * mm, y, libelle)
        c.setFillColor(MARINE)
        c.setFont("Sans-Gras", 10)
        texte = valeur if len(valeur) <= 75 else valeur[:72] + "…"
        c.drawString(marge + 52 * mm, y, texte)
        y -= 8 * mm

    # Identifiants de connexion (seulement à la création ou à la réinitialisation)
    if mot_de_passe:
        y -= 6 * mm
        hauteur = 34 * mm
        c.setFillColor(colors.HexColor("#FFF6DD"))
        c.setStrokeColor(OR)
        c.roundRect(marge, y - hauteur, larg - 2 * marge, hauteur, 3 * mm, stroke=1, fill=1)
        c.setFillColor(ROUGE)
        c.setFont("Sans-Gras", 11)
        c.drawString(marge + 5 * mm, y - 8 * mm, "Vos identifiants de connexion")
        c.setFillColor(MARINE)
        c.setFont("Sans", 10)
        c.drawString(marge + 5 * mm, y - 15 * mm, "Adresse du site :")
        c.drawString(marge + 5 * mm, y - 21 * mm, "Identifiant (matricule) :")
        c.drawString(marge + 5 * mm, y - 27 * mm, "Mot de passe provisoire :")
        c.setFont("Sans-Gras", 10)
        c.drawString(marge + 52 * mm, y - 15 * mm, settings.SITE_URL)
        c.drawString(marge + 52 * mm, y - 21 * mm, membre.matricule)
        c.drawString(marge + 52 * mm, y - 27 * mm, mot_de_passe)
        c.setFillColor(GRIS)
        c.setFont("Sans", 8.5)
        c.drawString(
            marge + 5 * mm,
            y - 32 * mm,
            "Ce mot de passe est à changer à la première connexion. Ne le communiquez à personne.",
        )

    # Pied de page
    c.setStrokeColor(OR)
    c.setLineWidth(1)
    c.line(marge, 20 * mm, larg - marge, 20 * mm)
    c.setFillColor(GRIS)
    c.setFont("Sans", 8)
    maintenant = timezone.localtime()
    c.drawString(marge, 14 * mm, f"Généré le {maintenant:%d/%m/%Y} à {maintenant:%H:%M}")
    c.drawRightString(
        larg - marge,
        14 * mm,
        "Congrégation Chrétienne de l'Ordre Sacré Éternel des Chérubins et Séraphins",
    )
    c.showPage()
