"""En-tête commun de l'Église sur tous les documents produits (décision du 20/11/2026).

Le même en-tête que la fiche d'identification : bandeau aux deux logos avec la Congrégation, le
Comité National de Coordination et le Bureau National de Commandement ; dessous, « Armée du
Salut du Bénin », le titre du document et la devise. Les courriers gardent leur modèle national
et l'autorisation sa carte (décisions précédentes).
"""

import io
from pathlib import Path

import pytest
from django.conf import settings
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4, A5, A6, landscape
from reportlab.pdfgen import canvas

from apps.membres.entete import MARQUES, entete_excel

MARQUES_TEXTE = [
    "CONGRÉGATION CHRÉTIENNE",
    "COMITÉ NATIONAL DE COORDINATION",
    "BUREAU NATIONAL DE COMMANDEMENT",
    "ARMÉE DU SALUT DU BÉNIN",
    "FOI – AMOUR – JUSTICE",
]


def marques_presentes(texte: str) -> bool:
    return all(m in texte for m in MARQUES_TEXTE)


def _ordre(pdf: bytes) -> dict:
    hauteurs = {}

    def noter(texte, cm, tm, police, taille):
        texte = texte.strip()
        if texte and texte not in hauteurs:
            hauteurs[texte] = tm[5]

    PdfReader(io.BytesIO(pdf)).pages[0].extract_text(visitor_text=noter)
    return hauteurs


@pytest.mark.parametrize("taille", [A4, landscape(A4), A5, landscape(A6)])
def test_entete_officiel_sur_tous_les_formats(taille):
    from apps.listes.exports import entete_officiel
    from apps.membres.pdf import _polices

    _polices()
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=taille)
    larg, haut = taille
    y = entete_officiel(c, "Quittance — essai", ["Sous-titre"], larg, haut)
    c.drawString(40, y, "CONTENU")
    c.showPage()
    c.save()
    h = _ordre(tampon.getvalue())

    def at(debut):
        return next(v for k, v in h.items() if k.startswith(debut))

    assert at("CONGRÉGATION") > at("COMITÉ NATIONAL") > at("BUREAU NATIONAL DE COMMANDEMENT")
    assert at("BUREAU NATIONAL DE COMMANDEMENT") > at("ARMÉE DU SALUT DU BÉNIN")
    assert at("ARMÉE DU SALUT DU BÉNIN") > at("QUITTANCE — ESSAI") > at("« FOI")
    assert at("« FOI") > at("Sous-titre") > at("CONTENU") > 0


def test_entete_excel():
    from openpyxl import Workbook

    ws = Workbook().active
    ligne = entete_excel(ws, "Liste des membres — Essai", ["Généré le 20/11/2026"], 3)
    valeurs = [c.value for rangee in ws.iter_rows(max_row=ligne - 1) for c in rangee if c.value]
    texte = " ".join(str(v) for v in valeurs)
    assert all(m in texte for m in MARQUES)
    assert "ARMÉE DU SALUT DU BÉNIN" in texte and "LISTE DES MEMBRES — ESSAI" in texte
    assert "Généré le 20/11/2026" in texte
    assert ws.cell(row=ligne, column=1).value is None  # première ligne libre
    assert len(ws._images) == 2  # les deux logos


def test_aucun_document_ne_dessine_son_propre_en_tete():
    """Tout document passe par l'en-tête commun (`apps/membres/entete.py`)."""
    racine = Path(settings.BASE_DIR) / "apps"
    fautifs = []
    for f in (
        list(racine.glob("*/pdf.py"))
        + list(racine.glob("*/exports.py"))
        + [racine / "evenements" / "views.py"]
    ):
        if f.parent.name in ("courrier",):  # modèle national des courriers (décision précédente)
            continue
        source = f.read_text(encoding="utf-8")
        if "ARMÉE DU SALUT DU BÉNIN" in source or "Armée du Salut du Bénin —" in source:
            fautifs.append(str(f.relative_to(racine)))
    assert fautifs == []
