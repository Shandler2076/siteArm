"""Corrections issues de la relecture finale de l'étape 2."""

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.membres.models import Membre, PhotoIdentite

URL = "/membres/bn/enregistrer/"


@pytest.fixture(autouse=True)
def prive(settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path
    return tmp_path


def _jpeg(larg=600, haut=800):
    b = io.BytesIO()
    Image.new("RGB", (larg, haut), (1, 2, 3)).save(b, "JPEG")
    return b.getvalue()


def _post(client, paroisse, **extra):
    d = {
        "nom": "Hounkpè",
        "prenoms": "Jean-Marc",
        "sexe": "M",
        "telephone": "0197000000",
        "date_naissance": "1990-05-01",
        "annee_integration": "2015",
        "paroisse_integration": paroisse.pk,
        "categorie": "actif",
    }
    d.update(extra)
    return client.post(URL, d)


# F1 — validations du formulaire d'enregistrement : jamais d'erreur 500
@pytest.mark.parametrize(
    "champ,valeur,message",
    [
        ("telephone", "abc", "téléphone invalide"),
        ("whatsapp", "zz", "téléphone invalide"),
        ("npi", "12", "10 chiffres"),
        ("annee_integration", "1800", "entre 1900"),
        ("annee_integration", "2099", "entre 1900"),
    ],
)
def test_saisie_invalide_message_et_pas_d_erreur_500(client, bn, paroisse, champ, valeur, message):
    r = _post(client, paroisse, **{champ: valeur})
    assert r.status_code == 200 and message in r.content.decode().lower()
    assert Membre.objects.count() == 0


def test_npi_deja_utilise_refuse_meme_apres_confirmation(client, bn, paroisse):
    _post(client, paroisse, npi="1234567890")
    r = _post(
        client,
        paroisse,
        nom="Autre",
        prenoms="Personne",
        npi="1234567890",
        confirmer_malgre_doublon="on",
    )
    assert r.status_code == 200 and "NPI" in r.content.decode()
    assert Membre.objects.count() == 1


# F2 — photo du CIP contrôlée
def test_cip_executable_refuse(client, bn, paroisse):
    r = _post(client, paroisse, photo_cip=SimpleUploadedFile("x.exe", b"MZ\x90\x00binaire"))
    assert r.status_code == 200 and "JPEG, PNG ou PDF" in r.content.decode()
    assert Membre.objects.count() == 0


def test_cip_pdf_accepte_et_servi_en_pdf(client, bn, client_bn, paroisse):
    _post(client, paroisse, photo_cip=SimpleUploadedFile("scan.pdf", b"%PDF-1.4\n%%EOF\n"))
    m = Membre.objects.get()
    assert m.photo_cip.name.endswith(".pdf") and "scan" not in m.photo_cip.name
    r = client_bn.get(f"/membres/{m.matricule}/cip/")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"


# F3 — CIP à resélectionner après l'avertissement de doublon
def test_cip_a_reselectionner_apres_doublon(client, bn, paroisse):
    _post(client, paroisse)
    r = _post(client, paroisse, photo_cip=SimpleUploadedFile("c.jpg", _jpeg()))
    assert "Sélectionnez à nouveau la photo du CIP" in r.content.decode()


# F4 — pas de fichier orphelin si l'enregistrement échoue
def test_pas_de_fichier_orphelin(paroisse, compte_bn, prive, monkeypatch):
    from apps.membres import services

    def echec(**kw):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(services.Affectation.objects, "create", echec)
    with pytest.raises(RuntimeError):
        services.enregistrer_membre(
            donnees={
                "nom": "A",
                "prenoms": "B",
                "sexe": "F",
                "telephone": "0197000000",
                "categorie": "actif",
                "photo_cip": SimpleUploadedFile("c.jpg", _jpeg()),
            },
            paroisse_integration=paroisse,
            annee_integration=2015,
            par=compte_bn,
        )
    assert not [p for p in Path(prive).rglob("*") if p.is_file()]


# F5 — image démesurée (bombe de décompression) refusée proprement
def test_image_demesuree_refusee(client_membre, monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    r = client_membre.post(
        "/membres/ma-fiche/photo/", {"fichier": SimpleUploadedFile("p.jpg", _jpeg(), "image/jpeg")}
    )
    assert r.status_code == 200 and "trop grande" in r.content.decode()
    assert PhotoIdentite.objects.count() == 0


# F6 — nom très long : la police se réduit pour tenir dans la largeur
def test_police_du_nom_ajustee():
    from reportlab.pdfbase.pdfmetrics import stringWidth

    from apps.membres.pdf import _ajuste, _polices, taille_pour_largeur

    _polices()
    assert taille_pour_largeur("HOUNKPÈ Jean", "Sans-Gras", 15, 360) == 15
    long_nom = "HOUNKPÈ-AGBANGLA Jean-Marc Sènakpon Comlan Dossou Kpadonou"
    t = taille_pour_largeur(long_nom, "Sans-Gras", 15, 360)
    assert 9 <= t < 15 and stringWidth(long_nom, "Sans-Gras", t) <= 360
    tres_long = long_nom * 3  # ne tient même pas en petit : coupé avec « … »
    t = taille_pour_largeur(tres_long, "Sans-Gras", 15, 360)
    coupe = _ajuste(tres_long, "Sans-Gras", t, 360)
    assert t == 9 and coupe.endswith("…") and stringWidth(coupe, "Sans-Gras", t) <= 360


# F7 — adresse du site obligatoire en production
def test_site_url_obligatoire_en_production():
    racine = Path(__file__).resolve().parents[3]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "PYTEST"))}
    env.update(
        {
            "DJANGO_DEBUG": "False",
            "DJANGO_ALLOWED_HOSTS": "exemple.bj",
            "DJANGO_SECRET_KEY": "k7#Qp2!vZr9@Lm4$Wt8^Hy1&Bn6*Xc3(Df5)Gs0-Ja+Ue7%Ri2=Oa9",
        }
    )
    r = subprocess.run(
        [sys.executable, "manage.py", "check"], cwd=racine, env=env, capture_output=True, text=True
    )
    assert r.returncode != 0 and "DJANGO_SITE_URL" in r.stderr


# F8 — on ne réinitialise pas le compte de quelqu'un qui a plus de droits que soi
def test_reinitialisation_refusee_si_droits_superieurs(client, paroisse, membre_enregistre):
    from django.contrib.auth.models import Permission

    from apps.comptes.models import Compte

    cible = membre_enregistre.membre.compte
    cible.user_permissions.add(
        *Permission.objects.filter(codename__in=["gerer_membres", "voir_cip"])
    )
    acteur = Compte.objects.create_user("BN2", "MotDePasse!2026", doit_changer_mot_de_passe=False)
    acteur.user_permissions.add(Permission.objects.get(codename="gerer_membres"))
    client.force_login(acteur)
    r = client.post(f"/membres/bn/{membre_enregistre.membre.matricule}/fiche-identifiants.pdf")
    assert r.status_code == 403
    cible.refresh_from_db()
    assert cible.check_password(membre_enregistre.mot_de_passe)


# F9 — le membre voit le motif du refus de sa photo
def test_motif_du_refus_affiche_au_membre(client_membre, client_bn):
    client_membre.post(
        "/membres/ma-fiche/photo/", {"fichier": SimpleUploadedFile("p.jpg", _jpeg(), "image/jpeg")}
    )
    p = PhotoIdentite.objects.get()
    client_bn.post(
        "/membres/bn/photos/", {"photo": p.pk, "decision": "refuser", "motif": "Pas en tenue"}
    )
    assert "Pas en tenue" in client_membre.get("/membres/ma-fiche/").content.decode()


# F10 — le BN peut ouvrir la photo du CIP depuis la fiche
def test_lien_cip_sur_la_fiche_bn(client_bn, membre_enregistre):
    m = membre_enregistre.membre
    m.photo_cip.save("cip.jpg", SimpleUploadedFile("cip.jpg", _jpeg()))
    html = client_bn.get(f"/membres/bn/{m.matricule}/").content.decode()
    assert f"/membres/{m.matricule}/cip/" in html
