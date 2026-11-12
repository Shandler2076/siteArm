"""Autorisation (carte de petit format) : photo, nom, événement, session, QR de vérification."""

import io

import segno
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.evenements.services import autorisation_valable
from apps.membres.pdf import (
    GRIS,
    LOGO_AS,
    LOGO_CONGREGATION,
    MARINE,
    OR,
    _ajuste,
    _image_photo,
    _polices,
)

LARGEUR, HAUTEUR = 85 * mm, 120 * mm


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
    m, ev = convocation.membre, convocation.evenement
    c.setStrokeColor(OR)
    c.setLineWidth(1.2)
    c.roundRect(x, y, LARGEUR, HAUTEUR, 3 * mm)
    haut = y + HAUTEUR
    for logo, lx in ((LOGO_CONGREGATION, x + 4 * mm), (LOGO_AS, x + LARGEUR - 15 * mm)):
        if logo.exists():
            c.drawImage(
                ImageReader(str(logo)),
                lx,
                haut - 15 * mm,
                11 * mm,
                11 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 8.5)
    c.drawCentredString(x + LARGEUR / 2, haut - 8 * mm, "ARMÉE DU SALUT DU BÉNIN")
    c.setFont("Sans-Gras", 9.5)
    c.drawCentredString(x + LARGEUR / 2, haut - 13 * mm, "AUTORISATION")
    # Photo
    px, py, pl, ph = x + 4 * mm, haut - 52 * mm, 28 * mm, 34 * mm
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
    c.drawImage(_qr(convocation), x + LARGEUR - 34 * mm, haut - 52 * mm, 30 * mm, 30 * mm)
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
    # Mention
    session = f" — {convocation.session.nom}" if convocation.session else ""
    c.setFillColor(MARINE)
    c.roundRect(x + 4 * mm, y + 6 * mm, LARGEUR - 8 * mm, 14 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Sans-Gras", 8.5)
    c.drawCentredString(x + LARGEUR / 2, y + 14.5 * mm, "Est autorisé(e) à travailler")
    c.setFont("Sans", 8)
    c.drawCentredString(
        x + LARGEUR / 2,
        y + 9.5 * mm,
        _ajuste(
            session.removeprefix(" — ") or "Toutes sessions", "Sans", 8, largeur_texte - 4 * mm
        ),
    )


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
