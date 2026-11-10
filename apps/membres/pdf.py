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

_polices_ok = False


def _polices():
    global _polices_ok
    if not _polices_ok:
        polices = STATIQUE / "fonts"
        pdfmetrics.registerFont(TTFont("Sans", str(polices / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("Sans-Gras", str(polices / "DejaVuSans-Bold.ttf")))
        _polices_ok = True


def _image_photo(membre: Membre):
    photo = membre.photo_acceptee
    if not photo:
        return None
    with photo.fichier.open("rb") as f:
        return ImageReader(io.BytesIO(f.read()))


def fiche_identification_pdf(membre: Membre, mot_de_passe: str | None = None) -> bytes:
    _polices()
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(f"Fiche d'identification — {membre.matricule}")
    c.setAuthor("Armée du Salut du Bénin")
    larg, haut = A4
    marge = 18 * mm

    # En-tête : logos et titre
    c.setFillColor(MARINE)
    c.rect(0, haut - 48 * mm, larg, 48 * mm, stroke=0, fill=1)
    c.setFillColor(ROUGE)
    c.rect(0, haut - 50 * mm, larg, 2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.roundRect(marge - 2 * mm, haut - 44 * mm, 40 * mm, 40 * mm, 4 * mm, stroke=0, fill=1)
    c.drawImage(ImageReader(str(LOGO_AS)), marge, haut - 42 * mm, 36 * mm, 36 * mm, mask="auto")
    c.roundRect(larg - marge - 46 * mm, haut - 44 * mm, 48 * mm, 40 * mm, 4 * mm, stroke=0, fill=1)
    c.drawImage(ImageReader(str(LOGO_CONGREGATION)), larg - marge - 45 * mm, haut - 41 * mm,
                46 * mm, 34.5 * mm, mask="auto", preserveAspectRatio=True)
    centre = (marge + 38 * mm + larg - marge - 46 * mm) / 2  # milieu entre les deux logos
    c.setFillColor(colors.white)
    c.setFont("Sans-Gras", 13.5)
    c.drawCentredString(centre, haut - 20 * mm, "ARMÉE DU SALUT DU BÉNIN")
    c.setFillColor(OR)
    c.setFont("Sans-Gras", 12)
    c.drawCentredString(centre, haut - 28 * mm, "FICHE D'IDENTIFICATION")
    c.setFillColor(colors.white)
    c.setFont("Sans", 9)
    c.drawCentredString(centre, haut - 36 * mm, "« FOI – AMOUR – JUSTICE »")

    # Matricule et photo
    y = haut - 64 * mm
    c.setFillColor(MARINE)
    c.roundRect(marge, y - 4 * mm, 92 * mm, 14 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Sans-Gras", 20)
    c.drawString(marge + 5 * mm, y, membre.matricule)
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 15)
    c.drawString(marge, y - 14 * mm, membre.nom_complet)

    px, py, pl, ph = larg - marge - 38 * mm, haut - 106 * mm, 38 * mm, 48 * mm
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
    y = haut - 112 * mm
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
            marge + 5 * mm, y - 32 * mm,
            "Ce mot de passe est à changer à la première connexion. "
            "Ne le communiquez à personne.",
        )

    # Pied de page
    c.setStrokeColor(OR)
    c.setLineWidth(1)
    c.line(marge, 20 * mm, larg - marge, 20 * mm)
    c.setFillColor(GRIS)
    c.setFont("Sans", 8)
    maintenant = timezone.localtime()
    c.drawString(marge, 14 * mm, f"Généré le {maintenant:%d/%m/%Y} à {maintenant:%H:%M}")
    c.drawRightString(larg - marge, 14 * mm,
                      "Congrégation Chrétienne de l'Ordre Sacré Éternel des Chérubins et Séraphins")
    c.showPage()
    c.save()
    return tampon.getvalue()
