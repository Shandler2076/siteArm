"""Acte de promotion (décision du BNC) et extrait pour un promu."""

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.listes.exports import MARGE, entete_officiel, pied_de_page
from apps.membres.pdf import MARINE, _ajuste, _polices


def _titre(acte) -> tuple[str, str]:
    from apps.grades.models import NatureActe

    titre = f"Décision n° {acte.numero} du {acte.date_decision:%d/%m/%Y}"
    if acte.nature == NatureActe.SPECIALE:
        objet = "portant promotion spéciale (article 84 du règlement intérieur)"
    else:
        s = acte.sessions.first()
        if s is None:
            epreuve = "le test"
        elif s.type == "examen":
            epreuve = f"l'examen du {s.date:%d/%m/%Y}"
        else:
            epreuve = f"le test du {s.date:%d/%m/%Y}"
        lieu = f" à {s.lieu}" if s and s.lieu else ""
        objet = f"portant promotion après {epreuve}{lieu}"
    return titre, objet


def acte_pdf(acte, seulement=None) -> bytes:
    """L'acte complet, ou l'extrait d'un seul promu (`seulement` : un membre)."""
    _polices()
    larg, haut = A4
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    titre, objet = _titre(acte)
    c.setTitle(titre)
    sous = [objet, f"Date d'effet : {acte.date_effet:%d/%m/%Y}"]
    if seulement is not None:
        sous.append("Extrait concernant un seul membre")
    y = entete_officiel(c, titre, sous, larg, haut)
    c.setFillColor(MARINE)
    c.setFont("Sans", 10)
    texte = "Le Bureau National de Commandement de l'Armée du Salut du Bénin décide :"
    c.drawString(MARGE, y, texte)
    y -= 7 * mm
    if acte.motif:
        c.setFont("Sans", 9)
        c.drawString(MARGE, y, _ajuste(f"Motif : {acte.motif}", "Sans", 9, larg - 2 * MARGE))
        y -= 6 * mm
    entetes = ["Matricule", "Prénoms et NOM", "Ancien grade", "Nouveau grade", "Paroisse"]
    largeurs = [31, 48, 30, 31, 34]
    c.setFont("Sans-Gras", 9)
    x = MARGE
    for t, w in zip(entetes, largeurs, strict=True):
        c.drawString(x, y, t)
        x += w * mm
    y -= 6 * mm
    c.setFont("Sans", 9)
    promotions = acte.promotions.select_related("membre").order_by("membre__nom", "membre__prenoms")
    if seulement is not None:
        promotions = promotions.filter(membre=seulement)
    for h in promotions:
        m = h.membre
        precedent = (
            m.grades.filter(date_effet__lte=h.date_effet)
            .exclude(pk=h.pk)
            .order_by("-date_effet", "-pk")
            .first()
        )
        a = m.affectation_actuelle
        valeurs = [
            m.matricule,
            f"{m.prenoms} {m.nom.upper()}",
            precedent.get_grade_display() if precedent else "—",
            h.get_grade_display(),
            a.paroisse.nom if a else "—",
        ]
        if y < 40 * mm:
            pied_de_page(c, 1, larg)
            c.showPage()
            _polices()
            c.setFont("Sans", 9)
            y = haut - 25 * mm
        x = MARGE
        for v, w in zip(valeurs, largeurs, strict=True):
            c.drawString(x, y, _ajuste(str(v), "Sans", 9, w * mm - 1 * mm))
            x += w * mm
        y -= 6 * mm
    y -= 12 * mm
    c.setFont("Sans", 10)
    c.drawString(larg - MARGE - 70 * mm, y, f"Fait le {acte.date_decision:%d/%m/%Y}")
    y -= 6 * mm
    c.drawString(larg - MARGE - 70 * mm, y, "Le Président du BNC,")
    y -= 22 * mm
    c.setFont("Sans-Gras", 10)
    c.drawString(larg - MARGE - 70 * mm, y, acte.signataire or "................................")
    pied_de_page(c, 1, larg)
    c.showPage()
    c.save()
    return tampon.getvalue()
