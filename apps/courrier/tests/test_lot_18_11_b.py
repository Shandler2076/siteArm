"""Remarques du mainteneur du 18/11/2026 après essai : aperçu, gras/souligné, nature « Autre »,
adresse sur deux lignes, recherche de bureau, ordre du formulaire."""

import io
from html import unescape

import pytest
from django.test import Client
from pypdf import PdfReader

from apps.bureaux.perimetre import Niveau, Unite
from apps.courrier import services as s
from apps.courrier.models import Courrier

NATIONAL = Unite(Niveau.NATIONAL, None)


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _html(r):
    return unescape(r.content.decode())


def _texte_pdf(contenu):
    return " ".join(
        " ".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages).split()
    )


# --- Adresse sur deux lignes --------------------------------------------------------------------
def test_adresse_sur_deux_lignes(bn):
    p1 = Unite(Niveau.PAROISSE, bn["P1"])
    assert s.adresse_proposee("lettre", "fr", bureaux=[p1]) == (
        "À\nMonsieur le Chef de l'Unité paroissiale de P1"
    )
    m1 = bn["m1"]
    assert s.adresse_proposee("lettre", "fr", membres=[m1]) == f"Au\n{m1.nom_complet}"
    m1.sexe = "F"
    assert s.adresse_proposee("lettre", "fr", membres=[m1]) == f"À la\n{m1.nom_complet}"
    assert s.adresse_proposee("lettre", "gun", bureaux=[p1]) == "Hlan\n"


# --- Nature « Autre » ---------------------------------------------------------------------------
def test_nature_autre_avec_titre(bn):
    from apps.courrier.pdf import courrier_pdf

    with pytest.raises(s.CourrierRefuse, match="titre"):
        s.preparer(
            unite=NATIONAL,
            nature="autre",
            objet="o",
            texte="t",
            bureaux=[f"paroisse-{bn['P1'].pk}"],
            par=bn["sn"].compte,
        )
    c = s.preparer(
        unite=NATIONAL,
        nature="autre",
        titre="Décision",
        objet="Nomination",
        texte="Article 1.",
        bureaux=[f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    assert c.titre == "DÉCISION"
    assert "DÉCISION" in _texte_pdf(courrier_pdf(c))


# --- Gras et souligné ---------------------------------------------------------------------------
def test_gras_et_souligne():
    assert s.mise_en_forme("Le **pèlerinage** aura lieu le __24 décembre__.") == (
        "Le <b>pèlerinage</b> aura lieu le <u>24 décembre</u>."
    )
    assert s.mise_en_forme("<script>**x**") == "&lt;script&gt;<b>x</b>"
    assert s.mise_en_forme("a ** b") == "a ** b"  # marque isolée : laissée telle quelle


def test_gras_dans_le_pdf(bn):
    from apps.courrier.pdf import courrier_pdf

    c = s.preparer(
        unite=NATIONAL,
        nature="lettre",
        objet="o",
        texte="Mot **important**.",
        bureaux=[f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    texte = _texte_pdf(courrier_pdf(c))
    assert "Mot important." in texte and "**" not in texte


# --- Aperçu -------------------------------------------------------------------------------------
def _donnees(bn, **kw):
    d = {
        "nature": "lettre",
        "mode": "redige",
        "lieu": "Porto-Novo",
        "objet": "Réunion",
        "texte": "Texte **gras**.",
        "langue": "fr",
        "police": "charis",
        "taille": "12",
        "bureaux": [f"paroisse-{bn['P1'].pk}"],
    }
    d.update(kw)
    return d


def test_apercu_sans_rien_enregistrer(bn):
    sn = _client(bn["sn"])
    r = sn.post("/courrier/national/apercu/", _donnees(bn))
    html = _html(r)
    assert r.status_code == 200 and "Réunion" in html and "<b>gras</b>" in html
    assert "BUREAU NATIONAL DE COMMANDEMENT" in html
    assert "Monsieur le Chef de l'Unité paroissiale de P1" in html
    r = sn.post("/courrier/national/apercu.pdf", _donnees(bn))
    assert r["Content-Type"] == "application/pdf" and "Réunion" in _texte_pdf(r.content)
    assert not Courrier.objects.exists()


def test_apercu_refuse_hors_de_ses_bureaux(bn):
    assert _client(bn["sec_p1"]).post("/courrier/national/apercu/", _donnees(bn)).status_code == 404


def test_apercu_signale_les_erreurs(bn):
    r = _client(bn["sn"]).post("/courrier/national/apercu/", _donnees(bn, objet=""))
    assert r.status_code == 200 and "objet" in _html(r).lower()


# --- Formulaire ---------------------------------------------------------------------------------
def test_formulaire_recherche_de_bureau_et_ordre(bn):
    html = _html(_client(bn["sn"]).get("/courrier/national/nouveau/"))
    assert 'id="liste-bureaux"' not in html  # plus de longue liste à cocher
    assert 'id="recherche-bureau"' in html and "donnees-bureaux" in html
    # Police en haut ; langue et adresse juste au-dessus du texte, puis le clavier.
    police, langue = html.index('name="police"'), html.index('name="langue"')
    adresse, texte = html.index('name="adresse"'), html.index('name="texte"')
    clavier = html.index('class="clavier"')
    assert police < langue < adresse < texte < clavier
    assert 'value="autre"' in html and "Aperçu" in html
    assert 'data-format="gras"' in html and 'data-format="souligne"' in html


def test_bureaux_choisis_par_la_recherche(bn):
    sn = _client(bn["sn"])
    sn.post("/courrier/national/nouveau/", _donnees(bn, bureaux=[f"paroisse-{bn['P2'].pk}"]))
    assert Courrier.objects.get().destinataires.get().unite_cle == f"paroisse-{bn['P2'].pk}"
