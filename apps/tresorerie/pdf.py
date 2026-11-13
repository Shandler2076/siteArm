"""Quittance d'une cotisation spéciale (A5, en-tête officiel)."""

import io

from django.utils import timezone
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.listes.exports import MARGE, entete_officiel, pied_de_page
from apps.membres.pdf import MARINE, _polices


def quittance_pdf(c) -> bytes:
    _polices()
    larg, haut = A5
    tampon = io.BytesIO()
    pdf = canvas.Canvas(tampon, pagesize=A5)
    pdf.setTitle(f"Quittance {c.quittance}")
    y = entete_officiel(pdf, "Quittance — cotisation spéciale", [c.cotisation.libelle], larg, haut)
    pour = c.membre.nom_complet if c.membre else c.unite_libelle
    matricule = c.membre.matricule if c.membre else ""
    lignes = [
        ("Quittance n°", c.quittance),
        ("Payé pour", pour),
        ("Matricule", matricule or "—"),
        ("Montant", f"{c.montant} F CFA"),
        ("Le", f"{timezone.localtime(c.date):%d/%m/%Y à %H:%M}"),
        ("Paiement", f"Mobile money — référence {c.paiement.reference}"),
    ]
    y -= 6 * mm
    for libelle, valeur in lignes:
        pdf.setFont("Sans-Gras", 10)
        pdf.setFillColor(MARINE)
        pdf.drawString(MARGE, y, libelle)
        pdf.setFont("Sans", 10)
        pdf.drawString(MARGE + 32 * mm, y, str(valeur))
        y -= 8 * mm
    pdf.setFont("Sans", 8)
    pdf.drawString(MARGE, y - 4 * mm, "Payé au Bureau national de commandement (numéro unique).")
    pied_de_page(pdf, 1, larg)
    pdf.showPage()
    pdf.save()
    return tampon.getvalue()
