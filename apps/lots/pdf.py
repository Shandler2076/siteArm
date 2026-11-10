"""PDF d'un lot validé : fiches avec identifiants, liste récapitulative."""

import io

from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.lots.models import Lot
from apps.membres.pdf import GRIS, MARINE, OR, _ajuste, _polices, dessiner_fiche
from apps.membres.services import generer_mot_de_passe_provisoire


def _membres(lot: Lot):
    return [
        x.membre
        for x in lot.lignes.filter(membre__isnull=False)
        .select_related("membre__compte", "membre__paroisse_integration")
        .order_by("numero")
    ]


def fiches_du_lot_pdf(lot: Lot, par) -> bytes:
    """Une fiche par membre du lot, chacune avec un NOUVEAU mot de passe provisoire."""
    membres = _membres(lot)
    mots = {m.pk: generer_mot_de_passe_provisoire() for m in membres}
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(f"Fiches d'identification — lot n° {lot.pk}")
    for m in membres:
        dessiner_fiche(c, m, mots[m.pk])
    c.save()
    contenu = tampon.getvalue()  # construit avant de toucher aux comptes
    with transaction.atomic():
        for m in membres:
            m.compte.set_password(mots[m.pk])
            m.compte.doit_changer_mot_de_passe = True
            m.compte.save(update_fields=["password", "doit_changer_mot_de_passe"])
    return contenu


def recapitulatif_pdf(lot: Lot) -> bytes:
    _polices()
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(f"Récapitulatif — lot n° {lot.pk}")
    larg, haut = A4
    marge = 16 * mm
    colonnes = [
        (marge, "N°"),
        (marge + 12 * mm, "Matricule"),
        (marge + 47 * mm, "Nom et prénoms"),
        (marge + 112 * mm, "Paroisse"),
        (marge + 158 * mm, "Catégorie"),
    ]

    def entete():
        c.setFillColor(MARINE)
        c.setFont("Sans-Gras", 13)
        c.drawString(marge, haut - 20 * mm, "ARMÉE DU SALUT DU BÉNIN — LISTE RÉCAPITULATIVE")
        c.setFont("Sans", 10)
        valide = timezone.localtime(lot.date_validation) if lot.date_validation else None
        c.drawString(
            marge,
            haut - 27 * mm,
            f"Lot n° {lot.pk} — Région {lot.region.code} {lot.region.nom}"
            + (f" — validé le {valide:%d/%m/%Y}" if valide else ""),
        )
        c.setStrokeColor(OR)
        c.line(marge, haut - 31 * mm, larg - marge, haut - 31 * mm)
        c.setFont("Sans-Gras", 9)
        for x, titre in colonnes:
            c.drawString(x, haut - 37 * mm, titre)
        return haut - 44 * mm

    def pied():
        c.setFillColor(GRIS)
        c.setFont("Sans", 8)
        maintenant = timezone.localtime()
        c.drawString(marge, 12 * mm, f"Généré le {maintenant:%d/%m/%Y} à {maintenant:%H:%M}")

    y = entete()
    for i, m in enumerate(_membres(lot), start=1):
        if y < 22 * mm:
            pied()
            c.showPage()
            y = entete()
        c.setFillColor(MARINE)
        c.setFont("Sans", 9)
        c.drawString(colonnes[0][0], y, str(i))
        c.drawString(colonnes[1][0], y, m.matricule)
        c.drawString(colonnes[2][0], y, _ajuste(m.nom_complet, "Sans", 9, 63 * mm))
        c.drawString(colonnes[3][0], y, _ajuste(m.paroisse_integration.nom, "Sans", 9, 44 * mm))
        c.drawString(colonnes[4][0], y, _ajuste(m.get_categorie_display(), "Sans", 9, 22 * mm))
        y -= 6.5 * mm
    pied()
    c.showPage()
    c.save()
    return tampon.getvalue()
