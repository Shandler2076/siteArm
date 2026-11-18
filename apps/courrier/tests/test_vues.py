import io
from html import unescape

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from pypdf import PdfReader

from apps.bureaux.perimetre import Niveau, Unite
from apps.courrier import services as s
from apps.courrier.models import Courrier, Destinataire, Etat
from apps.courrier.tests.conftest import image_signature

NATIONAL = Unite(Niveau.NATIONAL, None)


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _html(r):
    return unescape(r.content.decode())


def _texte_pdf(contenu: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages)


@pytest.fixture
def envoye(bn):
    c = s.preparer(
        unite=NATIONAL,
        nature="lettre",
        objet="Préparatifs de la Nativité",
        texte="Chers frères,\n\nNous vous informons. Ẹ̀ jẹ́ mì wá gbọ́n.",
        bureaux=[f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    s.deposer_signature(bn["president"].compte, image_signature())
    return s.valider(c, par=bn["president"].compte)


def test_parcours_complet_par_les_pages(bn):
    sn = _client(bn["sn"])
    r = sn.get("/courrier/national/nouveau/")
    assert r.status_code == 200 and "001-2026/CCOSECS-CNC/AS/BNC/SN" in _html(r)
    assert "Clavier goun" in _html(r)
    r = sn.post(
        "/courrier/national/nouveau/",
        {
            "nature": "lettre",
            "mode": "redige",
            "lieu": "Porto-Novo",
            "objet": "Réunion du bureau",
            "texte": "Texte du courrier.",
            "bureaux": [f"paroisse-{bn['P1'].pk}"],
            "membres": [str(bn["m4"].pk)],
        },
    )
    c = Courrier.objects.get()
    assert r.status_code == 302 and c.destinataires.count() == 2
    pres = _client(bn["president"])
    assert c.objet in _html(pres.get("/courrier/a-signer/"))
    pres.post("/courrier/ma-signature/", {"image": image_signature()})
    pres.post(f"/courrier/c/{c.pk}/action/", {"action": "valider", "version": c.version})
    c.refresh_from_db()
    assert c.etat == Etat.ENVOYE and c.numero == "001-2026/CCOSECS-CNC/AS/BNC/SN"
    # Le Secrétaire de P1 reçoit, ouvre, confirme.
    sec = _client(bn["sec_p1"])
    assert "Réunion du bureau" in _html(sec.get(f"/courrier/paroisse-{bn['P1'].pk}/recus/"))
    ligne = c.destinataires.get(type="bureau")
    assert ligne.recu_le is not None and ligne.lu_le is None
    assert "Courrier reçu" in _html(sec.get(f"/courrier/c/{c.pk}/"))
    sec.post(f"/courrier/c/{c.pk}/action/", {"action": "accuser", "ligne": ligne.pk})
    ligne.refresh_from_db()
    assert ligne.lu_le and ligne.accuse_le
    # Le membre désigné le voit dans « Mes courriers » ; l'expéditeur voit le suivi.
    assert "Réunion du bureau" in _html(_client(bn["m4"]).get("/courrier/moi/"))
    assert "Suivi des destinataires" in _html(sn.get(f"/courrier/c/{c.pk}/"))


@pytest.mark.parametrize("qui", ["m1", "m2", "chef"])
def test_courrier_invisible_hors_destinataires(envoye, bn, qui):
    c = _client(bn[qui])
    for url in (f"/courrier/c/{envoye.pk}/", f"/courrier/c/{envoye.pk}.pdf"):
        assert c.get(url).status_code == 404


def test_boite_d_un_autre_bureau_refusee(bn, client_technique):
    sec = _client(bn["sec_p1"])
    assert sec.get(f"/courrier/paroisse-{bn['P2'].pk}/recus/").status_code == 404
    assert sec.get("/courrier/national/nouveau/").status_code == 404
    # Même le compte technique n'ouvre pas la boîte d'un bureau dont il n'est pas responsable.
    assert client_technique.get(f"/courrier/paroisse-{bn['P1'].pk}/recus/").status_code == 404
    assert _client(bn["m1"]).get("/courrier/ma-signature/").status_code == 404


def test_recherche_limitee_au_perimetre(bn):
    sec = _client(bn["sec_p1"])
    url = f"/courrier/paroisse-{bn['P1'].pk}/recherche/"
    noms = [m["matricule"] for m in sec.get(url, {"q": "Test"}).json()["resultats"]]
    assert bn["m1"].matricule in noms and bn["m2"].matricule not in noms
    # Un membre hors périmètre envoyé à la main est refusé (aucun courrier préparé).
    sec.post(
        f"/courrier/paroisse-{bn['P1'].pk}/nouveau/",
        {
            "nature": "lettre",
            "mode": "redige",
            "objet": "o",
            "texte": "t",
            "membres": [bn["m2"].pk],
        },
    )
    assert not Courrier.objects.exists()


def test_signature_visible_par_son_proprietaire_seulement(bn, client_technique):
    s.deposer_signature(bn["president"].compte, image_signature())
    pres = _client(bn["president"])
    r = pres.get("/courrier/ma-signature/image.png")
    assert r.status_code == 200 and r["Cache-Control"] == "private, no-store"
    for autre in (client_technique, _client(bn["sn"])):
        assert autre.get("/courrier/ma-signature/image.png").status_code == 404


def test_pdf_au_format_du_modele(envoye, bn):
    r = _client(bn["sec_p1"]).get(f"/courrier/c/{envoye.pk}.pdf")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    texte = _texte_pdf(r.content)
    for attendu in (
        "BUREAU NATIONAL DE COMMANDEMENT",
        "001-2026/CCOSECS-CNC/AS/BNC/SN",
        "Porto-Novo, le",
        "Préparatifs de la Nativité",
        "Le Président",
        "TOKPOTA DAVO",
    ):
        assert attendu in texte
    assert "Email" not in texte and "@" not in texte


def test_pdf_local_communique_et_importe(bn):
    p1 = Unite(Niveau.PAROISSE, bn["P1"])
    bn["P1"].nom = "Gboa"
    bn["P1"].save()
    pdf_importe = SimpleUploadedFile("lettre goun.pdf", _un_pdf(), content_type="application/pdf")
    c = s.preparer(
        unite=p1,
        nature="communique",
        mode="importe",
        objet="Veillée",
        fichier=pdf_importe,
        bureaux=["national"],
        par=bn["sec_p1"].compte,
    )
    s.deposer_signature(bn["sec_p1"].compte, image_signature())
    c = s.valider(c, par=bn["sec_p1"].compte)
    from apps.courrier.pdf import courrier_pdf

    contenu = courrier_pdf(c)
    texte = _texte_pdf(contenu)
    assert "UNITÉ PAROISSIALE DE GBOA — RÉGION HOULENOU" in texte
    assert "COMMUNIQUÉ" in texte and "P.O. le Secrétaire paroissial" in texte
    assert "001-2026/CCOSECS-CNC/AS/UP-GBOA/S" in texte
    assert len(PdfReader(io.BytesIO(contenu)).pages) >= 2  # le PDF importé suit


def _un_pdf() -> bytes:
    from reportlab.pdfgen import canvas

    tampon = io.BytesIO()
    c = canvas.Canvas(tampon)
    c.drawString(100, 700, "Courrier ecrit a la main")
    c.save()
    return tampon.getvalue()


def test_pdf_avec_image_importee(bn):
    c = s.preparer(
        unite=NATIONAL,
        nature="lettre",
        mode="importe",
        objet="Scan",
        fichier=image_signature("scan.png"),
        bureaux=[f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    from apps.courrier.pdf import courrier_pdf

    assert "PROJET" in _texte_pdf(courrier_pdf(c))  # pas encore signé


def test_verification_publique(envoye):
    anonyme = Client()
    r = anonyme.get(f"/courrier/verifier/{envoye.jeton}/")
    assert r.status_code == 200 and "authentique" in _html(r)
    assert "Nous vous informons" not in _html(r)  # jamais le texte
    assert "Préparatifs" not in _html(r)  # ni l'objet
    assert "aucun courrier" in _html(anonyme.get("/courrier/verifier/faux-jeton/"))


def test_transmission_par_la_page(bn):
    c = s.preparer(
        unite=NATIONAL,
        nature="communique",
        objet="Communiqué de Noël",
        texte="Texte",
        niveaux=["paroisse"],
        par=bn["sn"].compte,
    )
    s.deposer_signature(bn["president"].compte, image_signature())
    s.valider(c, par=bn["president"].compte)
    sec = _client(bn["sec_p1"])
    assert "Transmettre aux membres" in _html(sec.get(f"/courrier/c/{c.pk}/"))
    sec.post(
        f"/courrier/c/{c.pk}/action/",
        {"action": "transmettre", "unite": f"paroisse-{bn['P1'].pk}"},
    )
    assert Destinataire.objects.filter(courrier=c, membre=bn["m1"]).exists()
    assert _client(bn["m1"]).get(f"/courrier/c/{c.pk}/").status_code == 200
    assert _client(bn["m2"]).get(f"/courrier/c/{c.pk}/").status_code == 404


def test_pages_bn_reservees(bn, envoye, client_technique):
    assert envoye.objet in _html(client_technique.get("/courrier/bn/registre/"))
    assert client_technique.get("/courrier/bn/clavier/").status_code == 200
    for qui in ("sec_p1", "m1"):
        c = _client(bn[qui])
        assert c.get("/courrier/bn/registre/").status_code == 404
        assert c.get("/courrier/bn/clavier/").status_code == 404


def test_journal_lisible(envoye, bn):
    from apps.journal.lecture import lire
    from apps.journal.models import EntreeJournal

    phrases = [ligne.texte for ligne in lire(EntreeJournal.objects.order_by("date"))]
    assert any("A préparé le courrier « Préparatifs" in p for p in phrases)
    assert any("A déposé l'image de sa signature" in p for p in phrases)
    assert any("A signé et envoyé le courrier n° 001-2026" in p for p in phrases)


def test_signature_sans_version_refusee_par_la_page(bn):
    c = s.preparer(
        unite=NATIONAL,
        nature="lettre",
        objet="o",
        texte="t",
        bureaux=["national"][:0] or [f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    s.deposer_signature(bn["president"].compte, image_signature())
    _client(bn["president"]).post(f"/courrier/c/{c.pk}/action/", {"action": "valider"})
    c.refresh_from_db()
    assert c.etat == Etat.A_SIGNER


@pytest.mark.parametrize("qui", ["m1", "sec_p1"])
def test_fichiers_et_actions_refuses_aux_autres(bn, qui):
    c = s.preparer(
        unite=NATIONAL,
        nature="lettre",
        objet="Confidentiel",
        mode="importe",
        fichier=image_signature("scan.png"),
        bureaux=[f"paroisse-{bn['P2'].pk}"],
        pieces=[image_signature("piece.png")],
        par=bn["sn"].compte,
    )
    s.deposer_signature(bn["president"].compte, image_signature())
    c = s.valider(c, par=bn["president"].compte)
    autre = _client(bn[qui])
    piece = c.pieces.get()
    assert autre.get(f"/courrier/c/{c.pk}/original/").status_code == 404
    assert autre.get(f"/courrier/c/{c.pk}/piece/{piece.pk}/").status_code == 404
    ligne = c.destinataires.get()
    assert (
        autre.post(
            f"/courrier/c/{c.pk}/action/", {"action": "accuser", "ligne": ligne.pk}
        ).status_code
        == 404
    )
    # Le destinataire (Chef de P2 = bn["chef"] ? non : Secrétaire/Chef de P2 absents) — le BN voit.
    assert _client(bn["sn"]).get(f"/courrier/c/{c.pk}/original/").status_code == 200


def test_nombre_de_requetes_stable_avec_beaucoup_de_destinataires(
    bn, nouveau_membre, django_assert_max_num_queries
):
    c = s.preparer(
        unite=NATIONAL,
        nature="communique",
        objet="Communiqué",
        texte="t",
        niveaux=["paroisse"],
        par=bn["sn"].compte,
    )
    s.deposer_signature(bn["president"].compte, image_signature())
    s.valider(c, par=bn["president"].compte)
    for i in range(15):
        nouveau_membre(bn["P1"], f"Membre{i}")
    s.transmettre_aux_membres(c, Unite(Niveau.PAROISSE, bn["P1"]), par=bn["sec_p1"].compte)
    m1 = _client(bn["m1"])
    with django_assert_max_num_queries(40):
        assert m1.get(f"/courrier/c/{c.pk}/").status_code == 200


def test_mots_proposes_par_le_site(bn):
    sec = _client(bn["sec_p1"])
    r = sec.get("/courrier/mots/", {"debut": "tọ"})
    assert r.status_code == 200 and r.json()["mots"][0] == "tọn"
    # Un membre simple n'écrit pas de courrier : pas de propositions.
    assert _client(bn["m1"]).get("/courrier/mots/", {"debut": "to"}).status_code == 404


def _envoi_local(bn, bureaux, membres=()):
    """Courrier du circuit Ekpe A (préparé et signé par son Chef)."""
    circuit = Unite(Niveau.CIRCUIT, bn["Ekpe A"])
    c = s.preparer(
        unite=circuit,
        nature="lettre",
        objet="Affaire du circuit",
        texte="Texte interne au circuit.",
        bureaux=bureaux,
        membres=list(membres),
        par=bn["chef"].compte,
    )
    s.deposer_signature(bn["chef"].compte, image_signature())
    return s.valider(c, par=bn["chef"].compte)


def test_bn_ne_voit_pas_les_courriers_entre_autres_niveaux(bn, client_technique):
    """Décision du 18/11/2026 : le BN ne voit que ce qu'il a envoyé ou ce qui lui est adressé."""
    c = _envoi_local(bn, [f"paroisse-{bn['P1'].pk}"], membres=[bn["m2"]])
    for client in (_client(bn["president"]), _client(bn["sn"]), client_technique):
        for url in (f"/courrier/c/{c.pk}/", f"/courrier/c/{c.pk}.pdf"):
            assert client.get(url).status_code == 404
        assert "Affaire du circuit" not in _html(client.get("/courrier/bn/registre/"))
    # Le destinataire, lui, le voit.
    assert _client(bn["sec_p1"]).get(f"/courrier/c/{c.pk}/").status_code == 200


def test_registre_national_courriers_recus_par_le_bn(bn):
    c = _envoi_local(bn, ["national"])
    sn = _client(bn["sn"])
    assert sn.get(f"/courrier/c/{c.pk}/").status_code == 200
    assert "Affaire du circuit" in _html(sn.get("/courrier/bn/registre/"))
