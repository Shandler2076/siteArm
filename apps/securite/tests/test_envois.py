"""Faille M4 : un envoi démesuré est refusé AVANT d'être reçu en entier."""

import io

import pytest
from PIL import Image

from apps.membres.images import PhotoInvalide, verifier_et_preparer_photo


@pytest.mark.django_db
def test_envoi_trop_gros_refuse_tot(client, settings):
    settings.TAILLE_MAX_ENVOI = 1000
    r = client.post("/connexion/", {"username": "x" * 2000, "password": "y"})
    assert r.status_code == 413 and "trop volumineux" in r.content.decode()


@pytest.mark.django_db
def test_envoi_normal_accepte(client):
    r = client.post("/connexion/", {"username": "x", "password": "y"})
    assert r.status_code == 200


@pytest.mark.parametrize("fmt", ["TIFF", "BMP", "GIF"])
def test_photo_seulement_jpeg_ou_png(fmt):
    tampon = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(tampon, fmt)
    tampon.seek(0)
    tampon.size = len(tampon.getvalue())
    with pytest.raises(PhotoInvalide, match="Format refusé"):
        verifier_et_preparer_photo(tampon)


def test_excel_lu_avec_defusedxml():
    """Faille M5 : les fichiers Excel (XML) sont lus sans risque d'entités XML piégées."""
    import openpyxl.xml

    assert openpyxl.xml.DEFUSEDXML


def test_versions_figees():
    from pathlib import Path

    lignes = [
        ligne
        for ligne in (Path(__file__).resolve().parents[3] / "requirements.txt")
        .read_text()
        .splitlines()
        if ligne.strip() and not ligne.startswith("#")
    ]
    assert lignes and all("==" in ligne for ligne in lignes)


@pytest.mark.django_db
def test_entete_permissions_policy(client):
    """Le site n'utilise ni caméra, ni micro, ni position : le navigateur les refuse d'office."""
    entete = client.get("/").headers["Permissions-Policy"]
    for api in ("camera=()", "microphone=()", "geolocation=()", "payment=()"):
        assert api in entete


def test_pillow_ne_tente_que_jpeg_et_png(monkeypatch):
    """Relecture : prouver que Pillow reçoit bien la liste des formats permis."""
    import apps.membres.images as images

    vus = []
    vrai_open = images.Image.open

    def espion(f, *a, **k):
        vus.append(k.get("formats"))
        return vrai_open(f, *a, **k)

    monkeypatch.setattr(images.Image, "open", espion)
    tampon = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(tampon, "PNG")
    tampon.seek(0)
    tampon.size = len(tampon.getvalue())
    verifier_et_preparer_photo(tampon)
    assert vus and all(set(f) == {"JPEG", "PNG"} for f in vus)
