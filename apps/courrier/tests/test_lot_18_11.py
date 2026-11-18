"""Remarques du mainteneur du 18/11/2026 sur la rubrique Courrier."""

import datetime
import io
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone
from pypdf import PdfReader

from apps.bureaux.perimetre import Niveau, Unite
from apps.courrier import services as s
from apps.courrier.models import Courrier, Etat
from apps.courrier.tests.conftest import image_signature

NATIONAL = Unite(Niveau.NATIONAL, None)


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _html(r):
    return unescape(r.content.decode())


def _texte_pdf(contenu):
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages)


def _preparer(bn, **kw):
    params = dict(
        unite=NATIONAL,
        nature="lettre",
        objet="Réunion",
        texte="Texte du courrier.",
        bureaux=[f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    params.update(kw)
    return s.preparer(**params)


def _signer(bn, c):
    if s.signature_active(bn["president"].compte) is None:
        s.deposer_signature(bn["president"].compte, image_signature())
    return s.valider(c, par=bn["president"].compte)


# --- Numéro automatique -------------------------------------------------------------------------
def test_numero_automatique_attribue_a_la_signature_sans_trou(bn):
    a, b, c = _preparer(bn), _preparer(bn), _preparer(bn)
    s.annuler(b, par=bn["sn"].compte)
    assert _signer(bn, c).numero.startswith("001-")  # ordre de signature, pas de préparation
    assert _signer(bn, a).numero.startswith("002-")  # le courrier abandonné ne laisse pas de trou


# --- Ligne d'adresse ----------------------------------------------------------------------------
def test_adresse_proposee_en_francais(bn):
    p1 = Unite(Niveau.PAROISSE, bn["P1"])
    assert s.adresse_proposee("lettre", "fr", bureaux=[p1]) == (
        "À\nMonsieur le Chef de l'Unité paroissiale de P1"
    )
    m1 = bn["m1"]
    assert s.adresse_proposee("lettre", "fr", membres=[m1]) == f"Au\n{m1.nom_complet}"
    m1.sexe = "F"
    assert s.adresse_proposee("lettre", "fr", membres=[m1]) == f"À la\n{m1.nom_complet}"
    assert s.adresse_proposee("communique", "fr") == "À l'attention de tous les bureaux"
    assert s.adresse_proposee("lettre", "gun", bureaux=[p1]) == "Hlan\n"


def test_adresse_goun_ecrite_a_la_main(bn):
    with pytest.raises(s.CourrierRefuse, match="Hlan"):
        _preparer(bn, langue="gun", adresse="Hlan")
    c = _preparer(bn, langue="gun", adresse="Hlan agun Ekpe tọn lẹpo")
    assert c.adresse == "Hlan agun Ekpe tọn lẹpo" and c.police == "charis"


def test_pdf_sans_le_mot_destinataire_avec_l_adresse(bn):
    from apps.courrier.pdf import courrier_pdf

    c = _signer(bn, _preparer(bn))
    texte = _texte_pdf(courrier_pdf(c))
    assert "Destinataire" not in texte
    assert "À Monsieur le Chef de l'Unité paroissiale de P1" in " ".join(texte.split())


# --- Polices et taille --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "police", ["liberation_serif", "liberation_sans", "charis", "gentium", "noto_serif"]
)
def test_cinq_polices_dans_le_pdf(bn, police):
    from apps.courrier.pdf import courrier_pdf

    c = _preparer(bn, police=police, texte="Ẹ̀ jẹ́ mì wá gbọ́n.")
    lecteur = PdfReader(io.BytesIO(courrier_pdf(c)))
    polices = str(lecteur.pages[0]["/Resources"]["/Font"].get_object())
    assert {
        "liberation_serif": "Liberation",
        "liberation_sans": "Liberation",
        "charis": "Charis",
        "gentium": "Gentium",
        "noto_serif": "Noto",
    }[police] in str(
        [
            lecteur.pages[0]["/Resources"]["/Font"][k]["/BaseFont"]
            for k in lecteur.pages[0]["/Resources"]["/Font"]
        ]
    ), polices


def test_taille_refusee_hors_liste(bn):
    with pytest.raises(s.CourrierRefuse, match="Taille"):
        _preparer(bn, taille=20)


def test_tenir_sur_une_page(bn):
    from apps.courrier.pdf import courrier_pdf

    long = "\n\n".join(["Paragraphe assez long pour remplir la page. " * 6] * 10)
    deux = _preparer(bn, texte=long, taille=13)
    assert len(PdfReader(io.BytesIO(courrier_pdf(deux))).pages) >= 2
    une = _preparer(bn, texte=long, taille=13, une_page=True)
    assert len(PdfReader(io.BytesIO(courrier_pdf(une))).pages) == 1


# --- En correction -------------------------------------------------------------------------------
def test_modifier_met_en_correction_et_bloque_la_signature(bn):
    c = _preparer(bn)
    s.deposer_signature(bn["president"].compte, image_signature())
    s.mettre_en_correction(c, par=bn["sn"].compte)
    c.refresh_from_db()
    assert c.etat == Etat.A_CORRIGER
    with pytest.raises(s.CourrierRefuse, match="correction"):
        s.valider(c, par=bn["president"].compte)
    s.modifier(c, objet="Réunion corrigée", texte="Nouveau texte", par=bn["sn"].compte)
    c.refresh_from_db()
    assert c.etat == Etat.A_CORRIGER  # enregistrer ne soumet pas
    s.soumettre_a_la_signature(c, par=bn["sn"].compte)
    c = s.valider(Courrier.objects.get(pk=c.pk), par=bn["president"].compte)
    assert c.envoye


def test_demande_de_correction_du_signataire_va_en_correction(bn):
    c = _preparer(bn)
    s.renvoyer(c, motif="Préciser la date", par=bn["president"].compte)
    sn = _client(bn["sn"])
    r = sn.get("/courrier/national/en-correction/")
    assert "Réunion" in _html(r) and "Préciser la date" in _html(r)


def test_parcours_correction_par_les_pages(bn):
    c = _preparer(bn)
    sn = _client(bn["sn"])
    r = sn.post(f"/courrier/c/{c.pk}/action/", {"action": "corriger"})
    assert r.status_code == 302 and r["Location"].endswith(f"/courrier/c/{c.pk}/modifier/")
    r = sn.post(
        f"/courrier/c/{c.pk}/modifier/",
        {
            "objet": "Objet corrigé",
            "texte": "Texte",
            "langue": "fr",
            "police": "gentium",
            "taille": "11",
            "soumettre": "1",
        },
    )
    c.refresh_from_db()
    assert c.etat == Etat.A_SIGNER and c.police == "gentium" and c.taille == 11


# --- Abandonnés ----------------------------------------------------------------------------------
def test_abandon_reprise_et_suppression(bn):
    c = _preparer(bn, pieces=[image_signature("piece.png")])
    s.annuler(c, par=bn["sn"].compte)
    sn = _client(bn["sn"])
    assert "Réunion" in _html(sn.get("/courrier/national/abandonnes/"))
    s.reprendre(Courrier.objects.get(pk=c.pk), par=bn["sn"].compte)
    assert Courrier.objects.get(pk=c.pk).etat == Etat.A_CORRIGER
    s.annuler(Courrier.objects.get(pk=c.pk), par=bn["sn"].compte)
    with pytest.raises(s.CourrierRefuse):
        s.supprimer(Courrier.objects.get(pk=c.pk), par=bn["m1"].compte)
    s.supprimer(Courrier.objects.get(pk=c.pk), par=bn["sn"].compte)
    assert not Courrier.objects.filter(pk=c.pk).exists()


def test_courrier_envoye_ne_se_supprime_jamais(bn):
    c = _signer(bn, _preparer(bn))
    with pytest.raises(s.CourrierRefuse):
        s.supprimer(c, par=bn["sn"].compte)


def test_effacement_automatique_apres_un_mois(bn):
    vieux, recent = _preparer(bn), _preparer(bn, objet="Récent")
    s.annuler(vieux, par=bn["sn"].compte)
    s.annuler(recent, par=bn["sn"].compte)
    Courrier.objects.filter(pk=vieux.pk).update(
        date_abandon=timezone.now() - datetime.timedelta(days=31)
    )
    from django.core.management import call_command

    call_command("purger_courriers_abandonnes")
    assert not Courrier.objects.filter(pk=vieux.pk).exists()
    assert Courrier.objects.filter(pk=recent.pk).exists()


# --- Menu ----------------------------------------------------------------------------------------
def test_menu_courrier_et_rubrique_toujours_marquee(bn):
    from apps.bureaux.tests.test_menu import _actifs, _menu

    sn = bn["sn"].compte
    menu = _menu(sn)
    groupe = next(g for g in menu if g.titre == "Courrier")
    libelles = [lien.libelle for lien in groupe.liens]
    for attendu in ("Nouveau courrier", "En correction", "Courriers abandonnés"):
        assert attendu in libelles
    c = _preparer(bn)
    s.mettre_en_correction(c, par=sn)
    r = _client(bn["sn"]).get(f"/courrier/c/{c.pk}/")
    assert 'class="actif" aria-current="page">En correction' in _html(r)
    assert _actifs(_menu(sn, "/courrier/national/nouveau/")) == [("Courrier", "Nouveau courrier")]


# --- Langue et clavier ---------------------------------------------------------------------------
def test_choix_de_la_langue_dans_le_formulaire(bn):
    html = _html(_client(bn["sn"]).get("/courrier/national/nouveau/"))
    assert 'name="langue" value="fr"' in html and 'name="langue" value="gun"' in html
    assert 'name="numero_ordre"' not in html  # numéro automatique
    for police in (
        "Charis SIL",
        "Gentium Plus",
        "Liberation Serif",
        "Liberation Sans",
        "Noto Serif",
    ):
        assert police in html


# --- Signature -----------------------------------------------------------------------------------
def test_changer_sa_signature_demande_le_mot_de_passe(bn):
    pres = bn["president"].compte
    pres.set_password("MotDePasse!2026")
    pres.save()
    s.deposer_signature(pres, image_signature())
    with pytest.raises(s.CourrierRefuse, match="Mot de passe"):
        s.deposer_signature(pres, image_signature(), mot_de_passe="faux")
    s.deposer_signature(pres, image_signature(), mot_de_passe="MotDePasse!2026")


def test_changer_sa_signature_demande_le_code_si_double_verification(bn):
    import time

    from apps.securite.models import DoubleVerification
    from apps.securite.totp import code_totp, nouveau_secret

    pres = bn["president"].compte
    pres.set_password("MotDePasse!2026")
    pres.save()
    secret = nouveau_secret()
    DoubleVerification.objects.create(compte=pres, secret=secret, active=True)
    s.deposer_signature(pres, image_signature())
    with pytest.raises(s.CourrierRefuse, match="Code"):
        s.deposer_signature(pres, image_signature(), mot_de_passe="MotDePasse!2026", code="000000")
    s.deposer_signature(
        pres, image_signature(), mot_de_passe="MotDePasse!2026", code=code_totp(secret, time.time())
    )


def test_signature_recadree_sur_le_trait(bn):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (600, 300), "white")
    ImageDraw.Draw(image).line((40, 200, 140, 230), fill="black", width=6)  # trait à gauche
    tampon = io.BytesIO()
    image.save(tampon, "PNG")
    sig = s.deposer_signature(
        bn["president"].compte, SimpleUploadedFile("s.png", tampon.getvalue(), "image/png")
    )
    with sig.image.open("rb") as f:
        largeur, _ = Image.open(f).size
    assert largeur < 150  # marges blanches retirées : l'image se centre sur le trait


# --- Corrections de la relecture ----------------------------------------------------------------
def test_adresse_coherente_avec_la_langue(bn):
    with pytest.raises(s.CourrierRefuse, match="Hlan"):
        _preparer(bn, langue="gun", adresse="Hlan,")
    with pytest.raises(s.CourrierRefuse, match="français"):
        _preparer(bn, langue="fr", adresse="Hlan agun lẹpo")
    c = _preparer(bn, langue="gun", adresse="Hlan agun lẹpo")
    s.mettre_en_correction(c, par=bn["sn"].compte)
    with pytest.raises(s.CourrierRefuse):
        s.modifier(c, objet="o", texte="t", langue="fr", par=bn["sn"].compte)
    c = s.modifier(c, objet="o", texte="t", langue="fr", adresse="", par=bn["sn"].compte)
    assert c.adresse.startswith("À\nMonsieur le Chef")  # vidée : le site propose de nouveau


def test_une_page_identique_pour_expediteur_et_destinataires(bn, nouveau_membre):
    from apps.courrier.pdf import courrier_pdf

    membres = [nouveau_membre(bn["P1"], f"Dest{i}") for i in range(6)]
    long = "\n\n".join(["Paragraphe assez long pour remplir la page. " * 6] * 7)
    c = _signer(bn, _preparer(bn, texte=long, membres=membres, une_page=True, taille=12))
    expediteur = courrier_pdf(c, avec_membres=True)
    destinataire = courrier_pdf(c, avec_membres=False)
    assert len(PdfReader(io.BytesIO(destinataire)).pages) == 1

    def tailles(contenu):
        page = PdfReader(io.BytesIO(contenu)).pages[0]
        vues = set()
        page.extract_text(visitor_text=lambda t, cm, tm, f, taille: vues.add(round(taille, 1)))
        return vues

    assert max(tailles(expediteur)) == max(tailles(destinataire))


def test_projet_sans_numero_perime(bn):
    from apps.courrier.pdf import courrier_pdf

    c = _preparer(bn)
    assert "numéro attribué à la signature" in " ".join(_texte_pdf(courrier_pdf(c)).split())


def test_journal_de_suppression_et_d_effacement(bn):
    from apps.journal.models import EntreeJournal

    a, b = _preparer(bn, objet="A supprimer"), _preparer(bn, objet="A effacer")
    s.annuler(a, par=bn["sn"].compte)
    s.annuler(b, par=bn["sn"].compte)
    s.supprimer(Courrier.objects.get(pk=a.pk), par=bn["sn"].compte)
    Courrier.objects.filter(pk=b.pk).update(
        date_abandon=timezone.now() - datetime.timedelta(days=40)
    )
    assert s.purger_abandonnes() == 1
    sup = EntreeJournal.objects.get(action="courrier_supprime")
    assert sup.details["courrier"] == a.pk and sup.details["objet"] == "A supprimer"
    purge = EntreeJournal.objects.get(action="courriers_purges")
    assert purge.unite == "national" and purge.details["objet"] == "A effacer"


def test_seuls_les_courriers_goun_alimentent_le_lexique(bn):
    from apps.courrier.models import MotClavier

    _signer(bn, _preparer(bn, texte="kplọ́zẹ xwẹ̀dọ"))  # courrier en français
    assert not MotClavier.objects.filter(mot="xwẹ̀dọ").exists()
    _signer(bn, _preparer(bn, langue="gun", adresse="Hlan agun", texte="xwẹ̀dọ"))
    assert MotClavier.objects.filter(mot="xwẹ̀dọ").exists()


def test_signature_refusee_si_un_membre_destinataire_est_sorti(bn):
    from apps.membres.models import Membre

    c = _preparer(bn, membres=[bn["m1"]])
    Membre.objects.filter(pk=bn["m1"].pk).update(statut="exclu")
    with pytest.raises(s.CourrierRefuse, match="ne peut plus recevoir"):
        _signer(bn, c)


def test_trop_de_mots_de_passe_faux_bloquent(bn):
    pres = bn["president"].compte
    pres.set_password("MotDePasse!2026")
    pres.save()
    s.deposer_signature(pres, image_signature())
    for _ in range(5):
        with pytest.raises(s.CourrierRefuse, match="Mot de passe"):
            s.deposer_signature(pres, image_signature(), mot_de_passe="faux")
    with pytest.raises(s.CourrierRefuse, match="Trop d'essais"):
        s.deposer_signature(pres, image_signature(), mot_de_passe="MotDePasse!2026")


@pytest.mark.parametrize("qui", ["sec_p1", "chef_p1", "m1"])
@pytest.mark.parametrize("action", ["corriger", "soumettre", "reprendre", "supprimer"])
def test_actions_du_preparateur_refusees_aux_autres(bn, qui, action):
    c = _preparer(bn)
    if action in ("reprendre", "supprimer"):
        s.annuler(c, par=bn["sn"].compte)
    elif action == "soumettre":
        s.mettre_en_correction(c, par=bn["sn"].compte)
    etat = Courrier.objects.get(pk=c.pk).etat
    _client(bn[qui]).post(f"/courrier/c/{c.pk}/action/", {"action": action})
    assert Courrier.objects.filter(pk=c.pk, etat=etat).exists()
