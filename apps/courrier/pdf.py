"""PDF d'un courrier ou d'un communiqué, au format du modèle national (séance du 16/11/2026).

Bandeau bleu marine avec filet or (logos, cinq lignes, la dernière au nom du bureau) ; numéro
d'ordre et lieu-date ; objet et ligne d'adresse (« À Monsieur le … », « Hlan … ») ; texte dans la
police et la taille choisies ; signataire avec sa signature déposée, centrée, et un QR code de
vérification ; pied de page au siège national (sans e-mail).
"""

import io
from xml.sax.saxutils import escape

import segno
from django.conf import settings
from django.urls import reverse
from django.utils import formats, timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from apps.courrier import services
from apps.courrier.models import TAILLE_MIN_UNE_PAGE
from apps.membres.pdf import LOGO_AS, LOGO_CONGREGATION, MARINE, OR, STATIQUE, _polices

# Polices des courriers (décision du 18/11/2026) : (fichier normal, fichier gras).
FICHIERS_POLICES = {
    "liberation_serif": ("LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf"),
    "liberation_sans": ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
    "charis": ("CharisSIL-Regular.ttf", "CharisSIL-Bold.ttf"),
    "gentium": ("GentiumPlus-Regular.ttf", "GentiumPlus-Bold.ttf"),
    "noto_serif": ("NotoSerif-Regular.ttf", "NotoSerif-Bold.ttf"),
}
_polices_courrier: set[str] = set()


def police_courrier(cle: str) -> str:
    """Nom ReportLab de la police (enregistrée une seule fois) ; DejaVu si fichier absent."""
    if cle not in FICHIERS_POLICES:
        return "Sans"
    nom = f"Courrier-{cle}"
    if cle not in _polices_courrier:
        dossier = STATIQUE / "fonts" / "courrier"
        normal, gras = FICHIERS_POLICES[cle]
        if not (dossier / normal).exists():
            return "Sans"
        pdfmetrics.registerFont(TTFont(nom, str(dossier / normal)))
        pdfmetrics.registerFont(TTFont(f"{nom}-Gras", str(dossier / gras)))
        registerFontFamily(
            nom, normal=nom, bold=f"{nom}-Gras", italic=nom, boldItalic=f"{nom}-Gras"
        )
        _polices_courrier.add(cle)
    return nom


JAUNE = colors.HexColor("#F7D417")
ORANGE = colors.HexColor("#F29A1F")
BORDEAUX = colors.HexColor("#7A1F2B")
MARGE = 18 * mm
HAUT_BANDEAU = 30 * mm
PIED = (
    "SIÈGE SOCIAL : C/N°135 TOKPOTA DAVO — BP : 800 PORTO-NOVO — "
    "Tél : +229-97-12-1321, +229-67-51-6393"
)
LIGNES_FIXES = [
    "CONGREGATION CHRETIENNE DE L'ORDRE SACRE ETERNEL",
    "DES CHERUBINS ET SERAPHINS ‘’MONT SION’’",
    "DU BENIN",
    "COMITE NATIONAL DE COORDINATION",
]


def url_verification(courrier) -> str:
    return settings.SITE_URL.rstrip("/") + reverse("courrier:verifier", args=[courrier.jeton])


def _oblique(c, x, y, texte, police, taille, couleur, centre=True):
    """Texte penché (les polices embarquées n'ont pas d'italique)."""
    c.saveState()
    c.setFillColor(couleur)
    c.setFont(police, taille)
    c.translate(x, y)
    c.skew(0, 12)
    if centre:
        c.drawCentredString(0, 0, texte)
    else:
        c.drawString(0, 0, texte)
    c.restoreState()


def _bandeau(c, larg, haut, derniere_ligne):
    y0 = haut - 8 * mm - HAUT_BANDEAU
    c.setFillColor(MARINE)
    c.rect(8 * mm, y0, larg - 16 * mm, HAUT_BANDEAU, stroke=0, fill=1)
    c.setFillColor(OR)
    c.rect(8 * mm, y0 - 2 * mm, larg - 16 * mm, 2 * mm, stroke=0, fill=1)
    cote = HAUT_BANDEAU - 6 * mm
    for logo, x in ((LOGO_CONGREGATION, 11 * mm), (LOGO_AS, larg - 11 * mm - cote)):
        c.setFillColor(colors.white)
        c.rect(x, y0 + 3 * mm, cote, cote, stroke=0, fill=1)
        if logo.exists():
            c.drawImage(
                ImageReader(str(logo)),
                x + 1 * mm,
                y0 + 4 * mm,
                cote - 2 * mm,
                cote - 2 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
    centre = larg / 2
    y = haut - 8 * mm - 6 * mm
    styles = [
        (colors.white, "Sans-Gras", 8.5),
        (JAUNE, "Sans-Gras", 8.5),
        (JAUNE, "Sans-Gras", 8.5),
        (ORANGE, "Sans-Gras", 7),
    ]
    for texte, (couleur, police, taille) in zip(LIGNES_FIXES, styles, strict=True):
        _oblique(c, centre, y, texte, police, taille, couleur)
        y -= 4.6 * mm
    largeur_max = larg - 2 * (11 * mm + cote + 3 * mm)
    taille = 11
    from reportlab.pdfbase.pdfmetrics import stringWidth

    while taille > 7 and stringWidth(derniere_ligne, "Sans-Gras", taille) > largeur_max:
        taille -= 0.5
    c.setFillColor(OR)
    c.setFont("Sans-Gras", taille)
    c.drawCentredString(centre, y - 1 * mm, derniere_ligne)


def _pied(c, larg, numero_page):
    c.setStrokeColor(BORDEAUX)
    c.setLineWidth(1.6)
    c.line(MARGE, 15 * mm, larg - MARGE, 15 * mm)
    c.setLineWidth(0.5)
    c.line(MARGE, 14 * mm, larg - MARGE, 14 * mm)
    c.setFillColor(colors.black)
    c.setFont("Sans-Gras", 6.8)
    c.drawCentredString(larg / 2, 10 * mm, PIED)
    c.setFont("Sans", 7)
    c.drawRightString(larg - MARGE, 6 * mm, f"Page {numero_page}")


def _styles(police: str = "Sans", taille: float = 10.5):
    base = ParagraphStyle("base", fontName=police, fontSize=taille, leading=round(taille * 1.4, 1))
    petit = max(7.5, taille - 1.5)
    return {
        "texte": ParagraphStyle(
            "texte", parent=base, alignment=TA_JUSTIFY, spaceAfter=round(taille * 0.6, 1)
        ),
        "petit": ParagraphStyle("petit", parent=base, fontSize=petit, leading=petit * 1.35),
        "gauche": ParagraphStyle("gauche", parent=base, alignment=TA_LEFT),
        "droite": ParagraphStyle("droite", parent=base, alignment=TA_RIGHT),
        "centre": ParagraphStyle("centre", parent=base, alignment=TA_CENTER),
        "titre": ParagraphStyle(
            "titre",
            parent=base,
            fontName=f"{police}-Gras" if police != "Sans" else "Sans-Gras",
            fontSize=taille + 5,
            leading=taille + 9,
            alignment=TA_CENTER,
            textColor=MARINE,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "signature": ParagraphStyle("signature", parent=base, alignment=TA_CENTER),
    }


# Tableaux de mise en page sans marge intérieure : tout s'aligne sur la marge du texte.
SANS_MARGE = [
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
]


def _date_fr(courrier) -> str:
    jour = timezone.localtime(courrier.date_envoi).date() if courrier.date_envoi else None
    return formats.date_format(jour, "j F Y") if jour else "……………"


def _paragraphes(texte: str, style) -> list:
    blocs = [b.strip() for b in (texte or "").replace("\r\n", "\n").split("\n\n")]
    return [Paragraph(escape(b).replace("\n", "<br/>"), style) for b in blocs if b]


def _image_courrier(fichier, largeur, hauteur) -> Image:
    fichier.open("rb")
    try:
        donnees = io.BytesIO(fichier.read())
    finally:
        fichier.close()
    lecteur = ImageReader(donnees)
    iw, ih = lecteur.getSize()
    echelle = min(largeur / iw, hauteur / ih)
    donnees.seek(0)
    return Image(donnees, iw * echelle, ih * echelle)


def _signature_reduite(fichier, largeur, hauteur) -> Image:
    """Signature réduite et posée sur fond blanc : le PDF ne contient pas l'image nette et
    transparente d'origine (rangée en stockage privé)."""
    from PIL import Image as PilImage

    fichier.open("rb")
    try:
        image = PilImage.open(io.BytesIO(fichier.read()))
        image.load()
    finally:
        fichier.close()
    image = image.convert("RGBA")
    cadre = image.getchannel("A").getbbox()  # recadrée sur le trait : vraiment centrée
    if cadre:
        image = image.crop(cadre)
    image.thumbnail((320, 130))
    fond = PilImage.new("RGB", image.size, "white")
    fond.paste(image, mask=image.getchannel("A"))
    sortie = io.BytesIO()
    fond.save(sortie, "JPEG", quality=70)
    sortie.seek(0)
    iw, ih = fond.size
    echelle = min(largeur / iw, hauteur / ih)
    return Image(sortie, iw * echelle, ih * echelle)


def _qr(courrier, cote) -> Image:
    tampon = io.BytesIO()
    segno.make(url_verification(courrier), error="m").save(
        tampon, kind="png", scale=6, dark="#14284B", border=1
    )
    tampon.seek(0)
    return Image(tampon, cote, cote)


def _bloc_signature(courrier, st) -> list:
    if courrier.qualite == "po":
        qualite = f"P.O. le {courrier.fonction_signataire}"
    elif courrier.fonction_signataire:
        qualite = f"Le {courrier.fonction_signataire}"
    else:
        qualite = "Le signataire"
    droite = [Paragraph(f"<b>{escape(qualite)}</b>", st["signature"])]
    if courrier.envoye and courrier.signature_id:
        try:
            droite.append(_signature_reduite(courrier.signature.image, 55 * mm, 22 * mm))
        except (OSError, ValueError):
            droite.append(Spacer(1, 18 * mm))
        droite.append(Paragraph(escape(courrier.nom_signataire), st["signature"]))
        gauche = [
            _qr(courrier, 24 * mm),
            Paragraph(
                "Authenticité : scannez ce code, ou ouvrez la page de vérification du site.",
                st["petit"],
            ),
        ]
    else:
        droite.append(Spacer(1, 18 * mm))
        droite.append(Paragraph("<i>(en attente de signature)</i>", st["signature"]))
        gauche = [Paragraph("<b>PROJET — non signé, non envoyé.</b>", st["petit"])]
    largeur = A4[0] - 2 * MARGE
    t = Table([[gauche, droite]], colWidths=[largeur * 0.45, largeur * 0.55])
    t.setStyle(
        TableStyle(
            [
                *SANS_MARGE,
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),  # titre, signature et nom alignés au centre
            ]
        )
    )
    return [Spacer(1, 8 * mm), KeepTogether(t)]


def _contenu(courrier, st, avec_membres=True, membre=None) -> list:
    largeur = A4[0] - 2 * MARGE
    numero = courrier.numero or "Projet — numéro attribué à la signature"
    gauche = [
        Paragraph(escape(numero), st["petit"]),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>{escape(courrier.expediteur_libelle)}</b>", st["gauche"]),
    ]
    droite = Paragraph(f"{escape(courrier.lieu)}, le {_date_fr(courrier)}", st["droite"])
    entete = Table([[gauche, droite]], colWidths=[largeur * 0.6, largeur * 0.4])
    entete.setStyle(TableStyle([*SANS_MARGE, ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flux = [entete, Spacer(1, 6 * mm)]
    objet = Paragraph(f"<b><u>Objet</u></b> : {escape(courrier.objet)}", st["gauche"])
    adresse = escape(courrier.adresse or "").replace("\n", "<br/>")
    if courrier.communique:
        flux += [
            Paragraph("COMMUNIQUÉ", st["titre"]),
            Paragraph(adresse or services.COMMUNIQUE_ADRESSE, st["centre"]),
            Spacer(1, 5 * mm),
            objet,
        ]
    else:
        # Pas de mot « Destinataire » : la formule d'adresse des lettres (18/11/2026).
        bloc = Table(
            [[objet, Paragraph(adresse, st["gauche"])]],
            colWidths=[largeur * 0.52, largeur * 0.48],
        )
        bloc.setStyle(
            TableStyle(
                [
                    *SANS_MARGE,
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (1, 0), (1, 0), 12),
                ]
            )
        )
        flux.append(bloc)
    flux.append(Spacer(1, 6 * mm))
    flux += _paragraphes(courrier.texte, st["texte"])
    if courrier.mode == "importe" and courrier.fichier:
        if courrier.fichier.name.lower().endswith(".pdf"):
            flux.append(
                Paragraph("<i>Le courrier importé figure aux pages suivantes.</i>", st["texte"])
            )
        else:
            try:
                flux.append(_image_courrier(courrier.fichier, largeur, 150 * mm))
            except (OSError, ValueError):
                flux.append(Paragraph("<i>Image du courrier illisible.</i>", st["texte"]))
    flux += _bloc_signature(courrier, st)
    pieces = list(courrier.pieces.all())
    if pieces:
        flux.append(Spacer(1, 4 * mm))
        flux.append(
            Paragraph(
                "<b>Pièces jointes :</b> " + escape(", ".join(p.nom for p in pieces)),
                st["petit"],
            )
        )
    directs = list(services.destinataires_directs(courrier)[:2000]) if avec_membres else []
    if not courrier.communique and len(directs) > 3:
        flux.append(Spacer(1, 4 * mm))
        flux.append(Paragraph("<b>Annexe — liste des destinataires</b>", st["gauche"]))
        flux += [Paragraph("• " + escape(d.libelle), st["petit"]) for d in directs]
    return flux


def _construire(courrier, st, avec_membres, membre) -> tuple[bytes, int]:
    unite = services.unite_expeditrice(courrier)
    derniere = services.ligne_bureau(unite) if unite else courrier.expediteur_libelle.upper()
    larg, haut = A4
    tampon = io.BytesIO()
    doc = BaseDocTemplate(
        tampon,
        pagesize=A4,
        title=f"{'Communiqué' if courrier.communique else 'Courrier'} — {courrier.objet}",
        author=courrier.expediteur_libelle,
    )
    cadre = Frame(
        MARGE,
        20 * mm,
        larg - 2 * MARGE,
        haut - 20 * mm - 8 * mm - HAUT_BANDEAU - 8 * mm,
        leftPadding=0,
        rightPadding=0,
    )

    def page(c, d):
        _bandeau(c, larg, haut, derniere)
        _pied(c, larg, d.page)

    doc.addPageTemplates([PageTemplate(id="courrier", frames=[cadre], onPage=page)])
    doc.build(_contenu(courrier, st, avec_membres=avec_membres, membre=membre))
    return tampon.getvalue(), doc.page


def courrier_pdf(courrier, avec_membres: bool = True, membre=None) -> bytes:
    _polices()
    registerFontFamily(
        "Sans", normal="Sans", bold="Sans-Gras", italic="Sans", boldItalic="Sans-Gras"
    )
    police = police_courrier(courrier.police)
    taille = float(courrier.taille or 12)
    # « Tenir sur une page » : le texte se resserre, jusqu'à 9 points au plus petit. La mesure se
    # fait sans l'annexe des destinataires (que seul l'expéditeur voit) : tout le monde reçoit le
    # même courrier, dans la même taille.
    if courrier.une_page and courrier.mode == "redige":
        _, pages = _construire(courrier, _styles(police, taille), False, None)
        while pages > 1 and taille > TAILLE_MIN_UNE_PAGE:
            taille = max(TAILLE_MIN_UNE_PAGE, taille - 0.5)
            _, pages = _construire(courrier, _styles(police, taille), False, None)
    contenu, _ = _construire(courrier, _styles(police, taille), avec_membres, membre)
    if courrier.mode == "importe" and courrier.fichier.name.lower().endswith(".pdf"):
        contenu = _ajouter_pdf_importe(contenu, courrier.fichier)
    return contenu


def _ajouter_pdf_importe(contenu: bytes, fichier) -> bytes:
    from pypdf import PdfReader, PdfWriter

    sortie = PdfWriter()
    sortie.append(PdfReader(io.BytesIO(contenu)))
    try:
        fichier.open("rb")
        try:
            sortie.append(PdfReader(io.BytesIO(fichier.read())))
        finally:
            fichier.close()
    except Exception:  # noqa: BLE001 — un PDF importé abîmé ne doit pas empêcher l'impression
        return contenu
    tampon = io.BytesIO()
    sortie.write(tampon)
    return tampon.getvalue()
