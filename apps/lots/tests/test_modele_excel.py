import io

from openpyxl import load_workbook

from apps.lots.colonnes import COLONNES
from apps.lots.modele_excel import modele_pour_region


def _classeur(region):
    return load_workbook(io.BytesIO(modele_pour_region(region)))


def test_modele_structure(territoire):
    wb = _classeur(territoire["HOULENOU"])
    ws = wb["Membres"]
    assert [c.value for c in ws[1]] == [col.entete for col in COLONNES]
    assert ws.freeze_panes == "A2"
    assert wb["Listes"].sheet_state == "hidden"
    paroisses = [c.value for c in wb["Listes"]["A"] if c.value]
    assert paroisses == ["P1", "P2", "P3"]
    assert "Consignes" in wb.sheetnames
    assert len(ws.data_validations.dataValidation) >= 4


def test_categories_et_consignes(territoire):
    wb = _classeur(territoire["HOULENOU"])
    categories = [c.value for c in wb["Listes"]["B"] if c.value]
    assert categories == ["Membre actif", "Membre d'honneur", "Membre sympathisant"]
    texte = " ".join(str(c.value) for row in wb["Consignes"].iter_rows() for c in row if c.value)
    assert "JJ/MM/AAAA" in texte and "membre actif" in texte.lower()


def test_paroisse_fermee_absente(territoire):
    territoire["P2"].fermer()
    wb = _classeur(territoire["HOULENOU"])
    assert "P2" not in [c.value for c in wb["Listes"]["A"]]


def test_telechargement_reserve_au_bn(client, client_technique, territoire, nouveau_membre):
    r = client_technique.get("/lots/modele/03.xlsx")
    assert r.status_code == 200
    assert r["Content-Disposition"].endswith('modele-membres-region-03.xlsx"')
    client.force_login(nouveau_membre(territoire["P1"], "X").compte)
    assert client.get("/lots/modele/03.xlsx").status_code == 403


def test_region_inconnue_404(client_technique, territoire):
    assert client_technique.get("/lots/modele/99.xlsx").status_code == 404
