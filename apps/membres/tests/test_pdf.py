import io

from pypdf import PdfReader

from apps.membres.pdf import fiche_identification_pdf


def _texte(pdf_bytes):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf_bytes)).pages)


def test_fiche_sans_identifiants(membre_enregistre):
    pdf = fiche_identification_pdf(membre_enregistre.membre)
    assert pdf.startswith(b"%PDF")
    t = _texte(pdf)
    assert "2015-03AS-0001" in t and "Camarade Jean-Marc HOUNKPÈ" in t and "FICHE D'IDENTIFICATION" in t
    assert "Membre actif" in t and "Ekpe A" in t
    assert "Mot de passe" not in t


def test_fiche_avec_identifiants(membre_enregistre):
    t = _texte(fiche_identification_pdf(membre_enregistre.membre, mot_de_passe="Ab3defGh7k"))
    assert "Ab3defGh7k" in t and "première connexion" in t


def test_impression_avec_identifiants_change_le_mot_de_passe(client_bn, membre_enregistre):
    m = membre_enregistre.membre
    url = f"/membres/bn/{m.matricule}/fiche-identifiants.pdf"
    assert client_bn.get(url).status_code == 405
    r = client_bn.post(url)
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    assert f'filename="fiche-{m.matricule}.pdf"' in r["Content-Disposition"]
    m.compte.refresh_from_db()
    assert not m.compte.check_password(membre_enregistre.mot_de_passe)
    assert m.compte.doit_changer_mot_de_passe
    mots = [w for w in _texte(r.content).split() if len(w) == 10 and m.compte.check_password(w)]
    assert len(mots) == 1


def test_fiche_sans_identifiants_bn(client_bn, membre_enregistre):
    r = client_bn.get(f"/membres/bn/{membre_enregistre.membre.matricule}/fiche.pdf")
    assert r.status_code == 200 and "Mot de passe" not in _texte(r.content)
