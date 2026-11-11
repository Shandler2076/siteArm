"""Exports officiels : liste des membres (PDF, Excel) et page de statistiques (PDF)."""

import datetime
import io

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.bureaux.perimetre import Unite
from apps.listes.colonnes import COLONNES_LISTE, lignes, preparer
from apps.listes.filtres import membres_filtres, resume_filtres
from apps.membres.models import Statut
from apps.membres.pdf import GRIS, LOGO_AS, LOGO_CONGREGATION, MARINE, OR, _ajuste, _polices

MARGE = 16 * mm
LARGEUR_PORTRAIT = A4[0] - 2 * MARGE  # 178 mm
LARGEUR_PAYSAGE = A4[1] - 2 * MARGE  # 265 mm


def _horodatage() -> str:
    maintenant = timezone.localtime()
    return f"Généré le {maintenant:%d/%m/%Y} à {maintenant:%H:%M}"


def _texte(v) -> str:
    return "" if v is None else str(v)


def entete_officiel(c: canvas.Canvas, titre: str, sous_titres: list[str], larg, haut) -> float:
    # Logo de l'Église à gauche, logo de l'Armée du Salut à droite.
    if LOGO_CONGREGATION.exists():
        c.drawImage(
            ImageReader(str(LOGO_CONGREGATION)),
            MARGE,
            haut - 26 * mm,
            16 * mm,
            14 * mm,
            mask="auto",
            preserveAspectRatio=True,
        )
    if LOGO_AS.exists():
        c.drawImage(
            ImageReader(str(LOGO_AS)),
            larg - MARGE - 14 * mm,
            haut - 26 * mm,
            14 * mm,
            14 * mm,
            mask="auto",
        )
    x = MARGE + 18 * mm
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 13)
    c.drawString(x, haut - 17 * mm, "ARMÉE DU SALUT DU BÉNIN")
    c.setFont("Sans-Gras", 11)
    c.drawString(x, haut - 23 * mm, _ajuste(titre, "Sans-Gras", 11, larg - x - MARGE - 18 * mm))
    y = haut - 31 * mm
    c.setFont("Sans", 9)
    for ligne in sous_titres:
        c.drawString(MARGE, y, _ajuste(ligne, "Sans", 9, larg - 2 * MARGE))
        y -= 4.5 * mm
    c.setStrokeColor(OR)
    c.setLineWidth(1.2)
    c.line(MARGE, y, larg - MARGE, y)
    return y - 6 * mm


def pied_de_page(c: canvas.Canvas, numero: int, larg) -> None:
    c.setFillColor(GRIS)
    c.setFont("Sans", 8)
    c.drawString(MARGE, 10 * mm, _horodatage())
    c.drawRightString(larg - MARGE, 10 * mm, f"Page {numero}")


def _en_tete_liste(unite: Unite, form, total: int) -> tuple[str, list[str]]:
    titre = f"Liste des membres — {unite.libelle}"
    sous = ["Filtres : " + " ; ".join(resume_filtres(form))]
    sous.append(f"{total} membre{'s' if total > 1 else ''}")
    return titre, sous


def liste_pdf(unite: Unite, form, aujourdhui: datetime.date) -> tuple[bytes, int]:
    _polices()
    colonnes = form.cleaned_data["colonnes"]
    qs = membres_filtres(unite, form.cleaned_data, aujourdhui)
    total = qs.count()
    largeurs = [COLONNES_LISTE[k][1] * mm for k in colonnes]
    somme = sum(largeurs)
    taille = A4 if somme <= LARGEUR_PORTRAIT else landscape(A4)
    utile = taille[0] - 2 * MARGE
    if somme > utile:
        largeurs = [w * utile / somme for w in largeurs]
    larg, haut = taille
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=taille)
    titre, sous = _en_tete_liste(unite, form, total)
    c.setTitle(titre)
    numero = 1

    def nouvelle_page() -> float:
        y = entete_officiel(c, titre, sous, larg, haut)
        c.setFillColor(MARINE)
        c.setFont("Sans-Gras", 8.5)
        x = MARGE
        for k, w in zip(colonnes, largeurs, strict=True):
            c.drawString(x, y, _ajuste(COLONNES_LISTE[k][0], "Sans-Gras", 8.5, w - 2 * mm))
            x += w
        return y - 6 * mm

    y = nouvelle_page()
    for rangee in lignes(preparer(qs, aujourdhui).iterator(chunk_size=500), colonnes, aujourdhui):
        if y < 18 * mm:
            pied_de_page(c, numero, larg)
            c.showPage()
            numero += 1
            y = nouvelle_page()
        c.setFillColor(MARINE)
        c.setFont("Sans", 8.5)
        x = MARGE
        for v, w in zip(rangee, largeurs, strict=True):
            c.drawString(x, y, _ajuste(_texte(v), "Sans", 8.5, w - 2 * mm))
            x += w
        y -= 5.5 * mm
    pied_de_page(c, numero, larg)
    c.showPage()
    c.save()
    return tampon.getvalue(), total


def liste_excel(unite: Unite, form, aujourdhui: datetime.date) -> tuple[bytes, int]:
    colonnes = form.cleaned_data["colonnes"]
    qs = membres_filtres(unite, form.cleaned_data, aujourdhui)
    classeur = Workbook()
    ws = classeur.active
    ws.title = "Membres"
    ws["A1"] = f"Armée du Salut du Bénin — Liste des membres — {unite.libelle}"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = _horodatage()
    ws["A3"] = "Filtres : " + " ; ".join(resume_filtres(form))
    for i, k in enumerate(colonnes, start=1):
        cellule = ws.cell(row=5, column=i, value=COLONNES_LISTE[k][0])
        cellule.font = Font(bold=True)
        ws.column_dimensions[cellule.column_letter].width = COLONNES_LISTE[k][1] * 0.6
    total = 0
    rangees = lignes(preparer(qs, aujourdhui).iterator(chunk_size=500), colonnes, aujourdhui)
    for n, rangee in enumerate(rangees, start=6):
        total += 1
        for i, v in enumerate(rangee, start=1):
            cellule = ws.cell(row=n, column=i, value=v)
            if isinstance(v, str):
                cellule.data_type = "s"  # jamais de formule (ex. nom saisi « =… »)
    ws.freeze_panes = "A6"
    tampon = io.BytesIO()
    classeur.save(tampon)
    return tampon.getvalue(), total


def statistiques_pdf(unite: Unite, sections, statuts: list[str]) -> bytes:
    _polices()
    larg, haut = A4
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    titre = f"Statistiques — {unite.libelle}"
    libelles = dict(Statut.choices)
    sous = ["Statut : " + (", ".join(str(libelles[s]) for s in statuts) or "tous")]
    c.setTitle(titre)
    numero = 1
    y = entete_officiel(c, titre, sous, larg, haut)
    for section in sections:
        besoin = (len(section.cellules) + 2) * 6 * mm
        if y - besoin < 18 * mm and besoin < haut - 60 * mm:
            pied_de_page(c, numero, larg)
            c.showPage()
            numero += 1
            y = entete_officiel(c, titre, sous, larg, haut)
        c.setFillColor(MARINE)
        c.setFont("Sans-Gras", 10.5)
        c.drawString(MARGE, y, section.titre)
        y -= 6.5 * mm
        for cellule in section.cellules:
            if y < 18 * mm:
                pied_de_page(c, numero, larg)
                c.showPage()
                numero += 1
                y = entete_officiel(c, titre, sous, larg, haut)
            c.setFillColor(MARINE)
            c.setFont("Sans", 9.5)
            c.drawString(MARGE + 4 * mm, y, _ajuste(cellule.libelle, "Sans", 9.5, 120 * mm))
            c.setFont("Sans-Gras", 9.5)
            c.drawRightString(MARGE + 150 * mm, y, str(cellule.nombre))
            y -= 5.5 * mm
        y -= 4 * mm
    pied_de_page(c, numero, larg)
    c.showPage()
    c.save()
    return tampon.getvalue()
