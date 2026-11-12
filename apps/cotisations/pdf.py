"""Documents PDF des cotisations : état des cotisations d'un membre, reçu de versement."""

import datetime
import io

from reportlab.lib.pagesizes import A4, A6, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.cotisations.regles import situation
from apps.cotisations.services import MOIS, nom_mois, periode
from apps.listes.exports import MARGE, entete_officiel, pied_de_page
from apps.membres.pdf import GRIS, MARINE, OR, _ajuste, _polices


def mention(s, mois_courant: datetime.date) -> str:
    if s.a_jour:
        return f"À jour au {nom_mois(mois_courant)}"
    return f"En retard de {s.retard} mois ({s.reste_du} F CFA)"


def etat_cotisations_pdf(membre, mois_courant: datetime.date) -> bytes:
    _polices()
    s = situation(membre, mois_courant)
    annee = mois_courant.year
    larg, haut = A4
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    titre = f"État des cotisations mensuelles — {annee}"
    c.setTitle(titre)
    y = entete_officiel(
        c, titre, [f"{membre.nom_complet} — matricule {membre.matricule}"], larg, haut
    )
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 12)
    c.drawString(MARGE, y, mention(s, mois_courant))
    y -= 10 * mm
    largeur = (larg - 2 * MARGE) / 4
    for i, nom in enumerate(MOIS):
        mois = datetime.date(annee, i + 1, 1)
        if mois in s.payes:
            etat = "Payé"
        elif mois in s.en_attente:
            etat = "En attente de validation"
        elif mois in s.dus:
            etat = "Non payé"
        else:
            etat = "Non dû"
        x = MARGE + (i % 4) * largeur
        ligne = y - (i // 4) * 14 * mm
        c.setStrokeColor(OR)
        c.rect(x + 1 * mm, ligne - 9 * mm, largeur - 2 * mm, 12 * mm)
        c.setFont("Sans-Gras", 9.5)
        c.setFillColor(MARINE)
        c.drawString(x + 3 * mm, ligne - 1 * mm, nom.capitalize())
        c.setFont("Sans", 8.5)
        c.setFillColor(GRIS)
        c.drawString(x + 3 * mm, ligne - 6 * mm, _ajuste(etat, "Sans", 8.5, largeur - 6 * mm))
    y -= 3 * 14 * mm + 8 * mm
    c.setFillColor(MARINE)
    c.setFont("Sans", 10.5)
    for texte in (
        f"Total versé en {annee} : {s.total_annee} F CFA",
        f"Total versé depuis le début : {s.total_depuis_debut} F CFA",
        f"Reste dû au {nom_mois(mois_courant)} : {s.reste_du} F CFA",
    ):
        c.drawString(MARGE, y, texte)
        y -= 6 * mm
    pied_de_page(c, 1, larg)
    c.showPage()
    c.save()
    return tampon.getvalue()


def recu_pdf(versement) -> bytes:
    _polices()
    larg, haut = landscape(A6)
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=(larg, haut))
    c.setTitle(f"Reçu {versement.numero_recu}")
    marge = 8 * mm
    c.setFillColor(MARINE)
    c.setFont("Sans-Gras", 11)
    c.drawString(marge, haut - 12 * mm, "ARMÉE DU SALUT DU BÉNIN")
    c.setFont("Sans-Gras", 10)
    c.drawString(marge, haut - 18 * mm, f"Reçu de cotisation n° {versement.numero_recu}")
    c.setStrokeColor(OR)
    c.line(marge, haut - 21 * mm, larg - marge, haut - 21 * mm)
    mois = list(versement.mois.values_list("mois", flat=True))
    lignes = [
        ("Membre", f"{versement.membre.nom_complet} ({versement.membre.matricule})"),
        ("Montant", f"{versement.montant} F CFA"),
        ("Mois", periode(mois)),
        ("Versé le", versement.date_versement.strftime("%d/%m/%Y")),
        ("Encaissé par", f"Paroisse {versement.paroisse.nom}"),
        ("Validé le", f"{versement.date_validation:%d/%m/%Y} par le circuit"),
    ]
    y = haut - 28 * mm
    for libelle, valeur in lignes:
        c.setFont("Sans-Gras", 8.5)
        c.setFillColor(GRIS)
        c.drawString(marge, y, libelle)
        c.setFont("Sans", 9)
        c.setFillColor(MARINE)
        c.drawString(marge + 26 * mm, y, _ajuste(valeur, "Sans", 9, larg - marge * 2 - 26 * mm))
        y -= 6 * mm
    c.showPage()
    c.save()
    return tampon.getvalue()
