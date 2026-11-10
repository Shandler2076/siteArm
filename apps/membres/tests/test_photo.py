import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.membres.models import PhotoIdentite

DEPOT = "/membres/ma-fiche/photo/"
FILE_BN = "/membres/bn/photos/"


def _image(larg=600, haut=800, fmt="JPEG", exif=False):
    b = io.BytesIO()
    im = Image.new("RGB", (larg, haut), (20, 40, 75))
    kw = {}
    if exif:
        e = Image.Exif()
        e[0x010F] = "Fabricant-Test"  # Make
        kw["exif"] = e
    im.save(b, fmt, **kw)
    return b.getvalue()


def _envoyer(client, contenu=None, nom="p.jpg"):
    contenu = _image() if contenu is None else contenu
    return client.post(DEPOT, {"fichier": SimpleUploadedFile(nom, contenu, "image/jpeg")})


@pytest.fixture(autouse=True)
def prive(settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path


def test_depot_puis_validation_bn(client_membre, client_bn, membre_enregistre):
    assert _envoyer(client_membre).status_code == 302
    photo = PhotoIdentite.objects.get()
    assert photo.etat == "en_attente" and membre_enregistre.membre.photo_acceptee is None
    client_bn.post(FILE_BN, {"photo": photo.pk, "decision": "accepter"})
    photo.refresh_from_db()
    assert photo.etat == "acceptee" and photo.decide_par.identifiant == "BN1"
    assert membre_enregistre.membre.photo_acceptee == photo


def test_nouvelle_photo_acceptee_remplace_l_ancienne(client_membre, client_bn, membre_enregistre):
    for _ in range(2):
        _envoyer(client_membre)
        p = PhotoIdentite.objects.filter(etat="en_attente").get()
        client_bn.post(FILE_BN, {"photo": p.pk, "decision": "accepter"})
    etats = sorted(PhotoIdentite.objects.values_list("etat", flat=True))
    assert etats == ["acceptee", "remplacee"]


def test_nouveau_depot_remplace_la_photo_en_attente(client_membre):
    _envoyer(client_membre)
    _envoyer(client_membre)
    assert PhotoIdentite.objects.filter(etat="en_attente").count() == 1


def test_refus_exige_un_motif(client_membre, client_bn):
    _envoyer(client_membre)
    p = PhotoIdentite.objects.get()
    r = client_bn.post(FILE_BN, {"photo": p.pk, "decision": "refuser", "motif": ""})
    assert "Indiquez le motif du refus." in r.content.decode()
    p.refresh_from_db()
    assert p.etat == "en_attente"
    client_bn.post(FILE_BN, {"photo": p.pk, "decision": "refuser", "motif": "Pas en tenue"})
    p.refresh_from_db()
    assert p.etat == "refusee" and p.motif_refus == "Pas en tenue"


def test_file_bn_reservee(client_membre):
    assert client_membre.get(FILE_BN).status_code == 403


@pytest.mark.parametrize("contenu,message", [
    (b"ceci n'est pas une image", "JPEG ou PNG"),
    (_image(200, 200), "trop petite"),
    (_image(fmt="GIF"), "JPEG ou PNG"),
])
def test_photo_refusee(client_membre, contenu, message):
    r = _envoyer(client_membre, contenu)
    assert message in r.content.decode() and PhotoIdentite.objects.count() == 0


def test_photo_trop_lourde(client_membre, settings):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
    r = _envoyer(client_membre, _image() + b"0" * (5 * 1024 * 1024))
    assert "5 Mo" in r.content.decode() and PhotoIdentite.objects.count() == 0


def test_photo_d_un_autre_membre_404(client, client_membre, membre_enregistre, paroisse, compte_bn):
    from apps.membres.services import enregistrer_membre

    _envoyer(client_membre)
    pk = PhotoIdentite.objects.get().pk
    assert client_membre.get(f"/membres/photos/{pk}/").status_code == 200
    autre = enregistrer_membre(
        donnees={"nom": "Autre", "prenoms": "Personne", "sexe": "F", "telephone": "0197111111",
                 "categorie": "actif"},
        paroisse_integration=paroisse, annee_integration=2016, par=compte_bn,
    ).membre
    autre.compte.doit_changer_mot_de_passe = False
    autre.compte.save()
    client.force_login(autre.compte)
    assert client.get(f"/membres/photos/{pk}/").status_code == 404


def test_bn_voit_la_photo(client_membre, client_bn):
    _envoyer(client_membre)
    pk = PhotoIdentite.objects.get().pk
    r = client_bn.get(f"/membres/photos/{pk}/")
    assert r.status_code == 200 and "no-store" in r["Cache-Control"]


def test_cip_reserve_au_bn(client_membre, client_bn, membre_enregistre):
    m = membre_enregistre.membre
    m.photo_cip.save("cip.jpg", SimpleUploadedFile("cip.jpg", _image()))
    assert client_membre.get(f"/membres/{m.matricule}/cip/").status_code == 404
    assert client_bn.get(f"/membres/{m.matricule}/cip/").status_code == 200


def test_metadonnees_supprimees_et_redimensionnee(client_membre):
    _envoyer(client_membre, _image(2000, 3000, exif=True))
    with PhotoIdentite.objects.get().fichier.open("rb") as f:
        im = Image.open(f)
        assert max(im.size) == 800 and not im.info.get("exif")


def test_fiche_affiche_la_photo_acceptee(client_membre, client_bn):
    _envoyer(client_membre)
    p = PhotoIdentite.objects.get()
    client_bn.post(FILE_BN, {"photo": p.pk, "decision": "accepter"})
    html = client_membre.get("/membres/ma-fiche/").content.decode()
    assert f"/membres/photos/{p.pk}/" in html
