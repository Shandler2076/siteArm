"""Autorisation (carte de petit format) : photo, nom, événement, rôle, section, QR code."""

import io

import segno
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.evenements.services import autorisation_valable
from apps.membres.pdf import (
    GRIS,
    LOGO_AS,
    LOGO_CONGREGATION_SANS_TEXTE,
    MARINE,
    OR,
    _ajuste,
    _image_photo,
    _polices,
)

LARGEUR, HAUTEUR = 85 * mm, 120 * mm
BORDEAUX = colors.HexColor("#8E1F35")
# En-tête : triangle et anges SANS le texte en courbe (le nom est écrit à côté ; 20/11/2026).
LOGO_EN_TETE = LOGO_CONGREGATION_SANS_TEXTE


def url_verification(convocation) -> str:
    chemin = reverse("evenements:verifier", args=[convocation.jeton])
    return settings.SITE_URL.rstrip("/") + chemin


def _qr(convocation) -> ImageReader:
    tampon = io.BytesIO()
    segno.make(url_verification(convocation), error="m").save(
        tampon, kind="png", scale=6, dark="#14284B", border=1
    )
    tampon.seek(0)
    return ImageReader(tampon)


def dessiner_carte(c: canvas.Canvas, convocation, x: float, y: float) -> None:
    """Carte de 85 × 120 mm dont le coin bas-gauche est (x, y)."""
    from apps.membres.pdf import filigrane

    m, ev = convocation.membre, convocation.evenement
    # Logo de l'Armée du Salut bien visible en filigrane ; AUTORISÉ passe dessus (20/11/2026).
    filigrane(c, x, y, LARGEUR, HAUTEUR, intensite=0.2)
    c.setStrokeColor(OR)
    c.setLineWidth(1.2)
    c.roundRect(x, y, LARGEUR, HAUTEUR, 3 * mm)
    haut = y + HAUTEUR
    for logo, lx, larg in (
        (LOGO_EN_TETE, x + 2.5 * mm, 15 * mm),
        (LOGO_AS, x + LARGEUR - 14.5 * mm, 11 * mm),
    ):
        if logo.exists():
            c.drawImage(
                ImageReader(str(logo)),
                lx,
                haut - 14.5 * mm,
                larg,
                11 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
    # En-tête comme les courriers (20/11/2026), sans leur fond : entre les deux logos, la
    # Congrégation, le Comité National de Coordination, le Bureau National de Commandement.
    from reportlab.pdfbase import pdfmetrics

    gauche, droite = x + 18 * mm, x + LARGEUR - 16 * mm
    centre, largeur_max = (gauche + droite) / 2, droite - gauche
    lignes = [
        ("CONGRÉGATION CHRÉTIENNE DE L'ORDRE SACRÉ ÉTERNEL", MARINE, 5.2),
        ("DES CHÉRUBINS ET SÉRAPHINS « MONT SION » DU BÉNIN", MARINE, 5.2),
        ("COMITÉ NATIONAL DE COORDINATION", BORDEAUX, 5.6),
        ("BUREAU NATIONAL DE COMMANDEMENT", MARINE, 6.6),
    ]
    ly = haut - 5.6 * mm
    for texte, couleur, taille in lignes:
        while taille > 4 and pdfmetrics.stringWidth(texte, "Sans-Gras", taille) > largeur_max:
            taille -= 0.1
        c.setFillColor(couleur)
        c.setFont("Sans-Gras", taille)
        c.drawCentredString(centre, ly, texte)
        ly -= 2.9 * mm
    c.setStrokeColor(OR)
    c.setLineWidth(0.8)
    c.line(x + 4 * mm, haut - 16.6 * mm, x + LARGEUR - 4 * mm, haut - 16.6 * mm)
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 9.5)
    c.drawCentredString(x + LARGEUR / 2, haut - 20.6 * mm, "AUTORISATION")
    # Photo
    px, py, pl, ph = x + 4 * mm, haut - 52 * mm, 26 * mm, 29 * mm
    c.setStrokeColor(MARINE)
    c.setLineWidth(0.6)
    c.rect(px, py, pl, ph)
    image = _image_photo(m)
    if image is not None:
        c.drawImage(image, px + 0.5, py + 0.5, pl - 1, ph - 1, preserveAspectRatio=True, anchor="c")
    else:
        c.setFillColor(GRIS)
        c.setFont("Sans", 7.5)
        c.drawCentredString(px + pl / 2, py + ph / 2, "Photo à venir")
    # QR code
    c.drawImage(_qr(convocation), x + LARGEUR - 32 * mm, haut - 51 * mm, 28 * mm, 28 * mm)
    c.setFillColor(GRIS)
    c.setFont("Sans", 6)
    c.drawCentredString(x + LARGEUR - 19 * mm, haut - 55 * mm, "Scanner pour vérifier")
    # Identité
    largeur_texte = LARGEUR - 8 * mm
    ty = haut - 62 * mm
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 10)
    c.drawString(x + 4 * mm, ty, _ajuste(m.nom_complet, "Sans-Gras", 10, largeur_texte))
    c.setFont("Sans", 8.5)
    c.drawString(x + 4 * mm, ty - 5 * mm, f"Matricule {m.matricule}")
    # Événement
    c.setStrokeColor(OR)
    c.line(x + 4 * mm, ty - 8 * mm, x + LARGEUR - 4 * mm, ty - 8 * mm)
    c.setFont("Sans-Gras", 9)
    c.drawString(x + 4 * mm, ty - 14 * mm, _ajuste(ev.nom, "Sans-Gras", 9, largeur_texte))
    debut = timezone.localtime(ev.debut)
    lieu = f" — {ev.lieu}" if ev.lieu else ""
    c.setFont("Sans", 8)
    c.drawString(
        x + 4 * mm,
        ty - 19 * mm,
        _ajuste(f"{debut:%d/%m/%Y à %H:%M}{lieu}", "Sans", 8, largeur_texte),
    )
    # Période de validité
    fin = timezone.localtime(ev.fin_validite)
    debut_v = timezone.localtime(ev.debut_validite)
    c.setFillColor(GRIS)
    c.setFont("Sans", 7)
    c.drawString(
        x + 4 * mm,
        ty - 25 * mm,
        _ajuste(
            f"Valable du {debut_v:%d/%m/%Y %H:%M} au {fin:%d/%m/%Y %H:%M}", "Sans", 7, largeur_texte
        ),
    )
    # Qualité, en grand (20/11/2026) : plus de « Est autorisé(e) à… » (AUTORISÉ est en
    # filigrane) ; en petit dessous, le poste au bureau d'organisation ou la section.
    from reportlab.pdfbase import pdfmetrics

    qualite, precision = convocation.qualite_autorisation, convocation.precision_autorisation
    c.setFillColor(MARINE)
    c.roundRect(x + 4 * mm, y + 6 * mm, LARGEUR - 8 * mm, 14 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    utile = largeur_texte - 6 * mm
    taille = min(14, 14 * utile / max(pdfmetrics.stringWidth(qualite, "Sans-Gras", 14), 1))
    taille = max(8, taille)  # jamais illisible ; au-delà, le texte est coupé avec « … »
    qualite = _ajuste(qualite, "Sans-Gras", taille, utile)
    c.setFont("Sans-Gras", taille)
    hauteur_qualite = y + (13.5 if precision else 11.5) * mm
    c.drawCentredString(x + LARGEUR / 2, hauteur_qualite, qualite)
    if precision:
        c.setFont("Sans", 8)
        c.drawCentredString(x + LARGEUR / 2, y + 8.5 * mm, _ajuste(precision, "Sans", 8, utile))
    from apps.membres.pdf import mot_filigrane

    mot_filigrane(c, x, y, LARGEUR, HAUTEUR, "AUTORISÉ")


def autorisation_pdf(convocation) -> bytes:
    _polices()
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=(LARGEUR + 10 * mm, HAUTEUR + 10 * mm))
    c.setTitle(f"Autorisation — {convocation.evenement.nom}")
    dessiner_carte(c, convocation, 5 * mm, 5 * mm)
    c.showPage()
    c.save()
    return tampon.getvalue()


def autorisations_pdf(evenement) -> bytes:
    """Toutes les autorisations valables, 4 cartes par page A4 (à découper)."""
    _polices()
    larg, haut = A4
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(f"Autorisations — {evenement.nom}")
    convocations = [
        x
        for x in evenement.convocations.filter(active=True).select_related(
            "membre", "session", "evenement"
        )
        if autorisation_valable(x)
    ]
    positions = [
        (12 * mm, haut - 12 * mm - HAUTEUR),
        (larg - 12 * mm - LARGEUR, haut - 12 * mm - HAUTEUR),
        (12 * mm, haut - 22 * mm - 2 * HAUTEUR),
        (larg - 12 * mm - LARGEUR, haut - 22 * mm - 2 * HAUTEUR),
    ]
    for i, convocation in enumerate(convocations):
        if i and i % 4 == 0:
            c.showPage()
        dessiner_carte(c, convocation, *positions[i % 4])
    if not convocations:
        c.setFont("Sans", 11)
        c.drawString(20 * mm, haut - 30 * mm, "Aucune autorisation valable.")
    c.showPage()
    c.save()
    return tampon.getvalue()
