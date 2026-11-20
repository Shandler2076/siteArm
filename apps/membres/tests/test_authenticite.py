"""Authenticité de la fiche d'identification (décision du 20/11/2026).

On ne peut pas empêcher de recopier un PDF, mais une fausse fiche se repère en quelques
secondes : chaque fiche porte un numéro, une date d'émission et un code QR vers une page
publique MINIMALE (authentique ou non, matricule, statut, numéro et date d'émission ; ni nom ni
photo). Une
réimpression remplace les fiches précédentes, qui deviennent « non valables ».
"""

import io
import re
from html import unescape

import pytest
from django.test import Client
from pypdf import PdfReader

from apps.membres.authenticite import emettre_fiche, etat_fiche, fiche_par_jeton
from apps.membres.models import FicheEmise
from apps.membres.pdf import fiche_identification_pdf


def _texte(pdf):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def _page(jeton):
    r = Client().get(f"/membres/verifier/{jeton}/")
    return r, unescape(r.content.decode())


def test_emission_numero_et_jeton(membre_enregistre, compte_bn):
    m = membre_enregistre.membre
    f = emettre_fiche(m, par=compte_bn)
    assert re.fullmatch(r"FI-\d{4}-\d{6}", f.numero)
    assert len(f.jeton) >= 32 and f.emise_par == compte_bn and f.remplacee_le is None
    assert fiche_par_jeton(f.jeton) == f
    assert etat_fiche(f)[0] == "authentique"


def test_reimpression_remplace_l_ancienne(membre_enregistre):
    m = membre_enregistre.membre
    ancienne = emettre_fiche(m)
    nouvelle = emettre_fiche(m)
    ancienne.refresh_from_db()
    assert ancienne.remplacee_le is not None and nouvelle.remplacee_le is None
    assert etat_fiche(ancienne)[0] == "remplacee"
    assert etat_fiche(None)[0] == "inconnue"


def test_le_pdf_porte_numero_date_et_code(membre_enregistre):
    m = membre_enregistre.membre
    t = _texte(fiche_identification_pdf(m))
    f = FicheEmise.objects.filter(membre=m).latest("pk")
    assert f.numero in t and "Émise le" in t
    assert "Scannez le code pour vérifier" in t
    # Une deuxième impression remplace la première.
    fiche_identification_pdf(m)
    assert FicheEmise.objects.filter(membre=m, remplacee_le__isnull=True).count() == 1


def test_page_publique_minimale(membre_enregistre):
    m = membre_enregistre.membre
    f = emettre_fiche(m)
    r, html = _page(f.jeton)
    assert r.status_code == 200
    assert "Fiche authentique" in html
    assert m.matricule in html and "Actif" in html
    assert f.emise_le.astimezone().strftime("%d/%m/%Y") in html
    assert f.numero in html
    # Décision du 20/11/2026 : jamais le nom sur la page publique.
    assert m.nom.upper() not in html.upper()
    assert m.nom_complet not in html
    # Rien de sensible : ni photo, ni téléphone, ni date de naissance.
    assert "<img" not in html.split("<main", 1)[-1]
    assert m.telephone not in html and "01/05/1990" not in html
    assert r["Cache-Control"] == "no-store" and r["X-Robots-Tag"] == "noindex"


def test_fiche_remplacee_ou_inconnue_non_valable(membre_enregistre):
    m = membre_enregistre.membre
    ancienne = emettre_fiche(m)
    emettre_fiche(m)
    r, html = _page(ancienne.jeton)
    assert r.status_code == 200 and "Fiche non valable" in html and "remplacée" in html
    assert m.nom_complet not in html
    r, html = _page("x" * 40)
    assert "Fiche non valable" in html and m.nom_complet not in html
    r, html = _page("pas un jeton !")
    assert r.status_code in (200, 404)
    assert m.nom_complet not in html


def test_statut_non_actif_bien_visible(membre_enregistre, compte_bn):
    import datetime

    from apps.membres.models import Statut
    from apps.mouvements.statuts import changer_statut

    m = membre_enregistre.membre
    f = emettre_fiche(m)
    changer_statut(m, Statut.EXCLU, par=compte_bn, date_effet=datetime.date.today(), motif="Test")
    r, html = _page(f.jeton)
    assert "Exclu" in html and "verification__alerte" in html


@pytest.mark.django_db
def test_jetons_tous_differents(membre_enregistre):
    m = membre_enregistre.membre
    jetons = {emettre_fiche(m).jeton for _ in range(5)}
    assert len(jetons) == 5


def test_petits_logos_en_filigrane_sur_toute_la_page(membre_enregistre):
    """Demande du 20/11/2026 : plusieurs petits logos de l'Armée du Salut en filigrane,
    couvrant toute la page de la fiche d'identification."""
    from apps.membres.pdf import FILIGRANE_FICHE_COLONNES, FILIGRANE_FICHE_LIGNES

    page = PdfReader(io.BytesIO(fiche_identification_pdf(membre_enregistre.membre))).pages[0]
    flux = page.get_contents().get_data()
    nb_logos = FILIGRANE_FICHE_COLONNES * FILIGRANE_FICHE_LIGNES
    assert nb_logos >= 20
    # Logos du filigrane + logos de l'en-tête + code QR.
    assert flux.count(b" Do") >= nb_logos + 3
