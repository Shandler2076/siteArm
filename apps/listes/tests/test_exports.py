import io

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.journal.models import EntreeJournal


@pytest.fixture
def client_sec(client, monde):
    client.force_login(monde["sec_p1"].compte)
    return client


def _base(monde, cle="P1"):
    return f"/bureau/paroisse-{monde[cle].pk}/listes/"


def _texte(contenu):
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages)


def test_pdf(client_sec, monde):
    r = client_sec.get(_base(monde) + "pdf/")
    assert r["Content-Type"] == "application/pdf"
    assert r["Content-Disposition"].startswith("attachment;")
    assert "no-store" in r["Cache-Control"]
    texte = _texte(r.content)
    assert "ARMÉE DU SALUT DU BÉNIN" in texte and "Généré le" in texte
    assert "Adjovi" in texte and "Bio" not in texte and "3 membres" in texte
    page = PdfReader(io.BytesIO(r.content)).pages[0]
    assert page.mediabox.width < page.mediabox.height


def test_pdf_paysage_si_beaucoup_de_colonnes(client_sec, monde):
    from apps.listes.colonnes import COLONNES_LISTE

    q = "?envoye=1&" + "&".join(f"colonnes={c}" for c in COLONNES_LISTE)
    r = client_sec.get(_base(monde) + "pdf/" + q)
    page = PdfReader(io.BytesIO(r.content)).pages[0]
    assert page.mediabox.width > page.mediabox.height
    assert "Secrétaire paroissial" in _texte(r.content)


def test_excel(client_sec, monde):
    r = client_sec.get(
        _base(monde) + "excel/?envoye=1&statut=actif&colonnes=matricule&colonnes=nom"
    )
    assert r["Content-Type"].startswith("application/vnd.openxmlformats")
    ws = load_workbook(io.BytesIO(r.content)).active
    assert ws["A1"].value.startswith("Armée du Salut du Bénin")
    assert ws["A2"].value.startswith("Généré le")
    assert "Statut : Actif" in ws["A3"].value
    assert [c.value for c in ws[5]] == ["Matricule", "Nom"]
    assert sorted(ws.cell(row=i, column=2).value for i in range(6, ws.max_row + 1)) == [
        "Adjovi",
        "Secretaire",
        "Tresorier",
    ]


def test_excel_pas_de_formule(client_sec, monde):
    m1 = monde["m1"]
    m1.nom = '=HYPERLINK("http://x","clic")'
    m1.save()
    r = client_sec.get(_base(monde) + "excel/?envoye=1&colonnes=nom&colonnes=telephone")
    ws = load_workbook(io.BytesIO(r.content)).active
    valeurs = {ws.cell(row=i, column=1).value: ws.cell(row=i, column=1) for i in range(6, 9)}
    cellule = valeurs['=HYPERLINK("http://x","clic")']
    assert cellule.data_type == "s"
    assert ws.cell(row=6, column=2).data_type == "s"  # téléphone en texte


def test_journal(client_sec, monde):
    client_sec.get(_base(monde) + "pdf/?envoye=1&sexe=M")
    client_sec.get(_base(monde) + "excel/")
    e1, e2 = EntreeJournal.objects.filter(
        action__in=["liste_pdf", "liste_excel", "statistiques_pdf", "tranches_age"]
    ).order_by("date", "pk")
    assert (e1.action, e2.action) == ("liste_pdf", "liste_excel")
    assert e1.auteur == monde["sec_p1"].compte and e1.unite == f"paroisse-{monde['P1'].pk}"
    assert e1.details["lignes"] == 3 and "sexe=M" in e1.details["filtres"]


def test_export_hors_perimetre_404(client_sec, monde):
    assert client_sec.get(_base(monde, "P2") + "pdf/").status_code == 404
    assert client_sec.get(_base(monde, "P2") + "excel/").status_code == 404
    assert not EntreeJournal.objects.filter(
        action__in=["liste_pdf", "liste_excel", "statistiques_pdf", "tranches_age"]
    ).exists()


def test_export_formulaire_invalide_redirige(client_sec, monde):
    r = client_sec.get(_base(monde) + "pdf/?envoye=1&age=plus")
    assert r.status_code == 302 and r.url.startswith(_base(monde))
    assert not EntreeJournal.objects.filter(
        action__in=["liste_pdf", "liste_excel", "statistiques_pdf", "tranches_age"]
    ).exists()


def test_affichage_non_journalise(client_sec, monde):
    client_sec.get(_base(monde))
    assert not EntreeJournal.objects.filter(
        action__in=["liste_pdf", "liste_excel", "statistiques_pdf", "tranches_age"]
    ).exists()
