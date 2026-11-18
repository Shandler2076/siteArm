import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.bureaux.perimetre import Niveau, Unite
from apps.courrier import services as s
from apps.courrier.models import Courrier, Destinataire, Etat, MotClavier, SignatureDeposee
from apps.courrier.tests.conftest import image_signature
from apps.journal.models import EntreeJournal
from apps.notifications.models import Notification

NATIONAL = Unite(Niveau.NATIONAL, None)


def _p1(bn):
    return Unite(Niveau.PAROISSE, bn["P1"])


def _preparer(bn, **kw):
    params = dict(
        unite=NATIONAL,
        nature="lettre",
        objet="Préparatifs de la Nativité",
        texte="Chers frères,\nNous vous informons…",
        bureaux=[f"paroisse-{bn['P1'].pk}"],
        par=bn["sn"].compte,
    )
    params.update(kw)
    return s.preparer(**params)


def _signer(compte):
    s.deposer_signature(compte, image_signature())


# --- Numéro d'ordre ------------------------------------------------------------------------------
def test_numero_complet_national_et_local(bn):
    assert s.numero_complet(NATIONAL, 12, 2026) == "012-2026/CCOSECS-CNC/AS/BNC/SN"
    bn["P1"].nom = "Gboa"
    assert s.numero_complet(_p1(bn), 7, 2026) == "007-2026/CCOSECS-CNC/AS/UP-GBOA/S"
    circuit = Unite(Niveau.CIRCUIT, bn["Ekpe A"])
    assert s.numero_complet(circuit, 1, 2026) == "001-2026/CCOSECS-CNC/AS/SC-EKPE-A/S"
    region = Unite(Niveau.REGION, bn["WEME"])
    assert s.numero_complet(region, 3, 2026).endswith("/AS/BRC-WEME/S")


def test_numero_propose_suit_chaque_bureau_et_repart_chaque_annee(bn):
    assert s.proposer_numero(NATIONAL, 2026) == 1
    c = _preparer(bn)
    assert c.numero_ordre == 1
    _signer(bn["president"].compte)
    s.valider(c, par=bn["president"].compte)
    assert s.proposer_numero(NATIONAL, 2026) == 2
    assert s.proposer_numero(NATIONAL, 2027) == 1
    assert s.proposer_numero(_p1(bn), 2026) == 1  # suite propre au bureau


def test_numero_deja_employe_refuse(bn):
    _signer(bn["president"].compte)
    s.valider(_preparer(bn, numero_ordre=5), par=bn["president"].compte)
    with pytest.raises(s.CourrierRefuse, match="déjà"):
        _preparer(bn, numero_ordre=5)


# --- Préparation ---------------------------------------------------------------------------------
def test_preparer_exige_un_destinataire_et_un_texte(bn):
    with pytest.raises(s.CourrierRefuse, match="destinataire"):
        _preparer(bn, bureaux=[])
    with pytest.raises(s.CourrierRefuse, match="texte"):
        _preparer(bn, texte="  ")


def test_niveaux_entiers_et_tous_les_bureaux(bn):
    c = _preparer(bn, nature="communique", bureaux=[], niveaux=["region", "circuit", "paroisse"])
    assert c.destinataires.count() == 2 + 3 + 4
    assert c.etat == Etat.A_SIGNER


def test_bureau_local_ecrit_au_bn_et_plus_bas_seulement(bn):
    chef = bn["chef"].compte  # Chef de Section de Circuit Ekpe A
    circuit = Unite(Niveau.CIRCUIT, bn["Ekpe A"])
    c = s.preparer(
        unite=circuit,
        nature="lettre",
        objet="Rapport",
        texte="Texte",
        bureaux=["national", f"paroisse-{bn['P1'].pk}"],
        par=chef,
    )
    assert {d.unite_cle for d in c.destinataires.all()} == {"national", f"paroisse-{bn['P1'].pk}"}
    for interdit in (f"paroisse-{bn['P3'].pk}", f"region-{bn['HOULENOU'].pk}"):
        with pytest.raises(s.CourrierRefuse):
            s.preparer(
                unite=circuit, nature="lettre", objet="o", texte="t", bureaux=[interdit], par=chef
            )
    # Membres : seulement ceux du périmètre du bureau.
    with pytest.raises(s.CourrierRefuse):
        s.preparer(
            unite=circuit, nature="lettre", objet="o", texte="t", membres=[bn["m4"]], par=chef
        )


def test_preparer_reserve_aux_bureaux_du_compte(bn):
    with pytest.raises(s.CourrierRefuse):
        _preparer(bn, par=bn["m1"].compte)
    with pytest.raises(s.CourrierRefuse):
        _preparer(bn, unite=_p1(bn), par=bn["chef"].compte)


def test_import_exige_un_fichier_valide(bn):
    with pytest.raises(s.CourrierRefuse, match="fichier"):
        _preparer(bn, mode="importe", texte="")
    faux = SimpleUploadedFile("lettre.pdf", b"pas un pdf", content_type="application/pdf")
    with pytest.raises(s.CourrierRefuse, match="Format"):
        _preparer(bn, mode="importe", texte="", fichier=faux)
    from apps.courrier.tests.test_vues import _un_pdf

    vrai = SimpleUploadedFile("lettre.pdf", _un_pdf(), content_type="application/pdf")
    c = _preparer(bn, mode="importe", texte="", fichier=vrai)
    assert c.fichier.name.endswith(".pdf")


# --- Signature et validation ---------------------------------------------------------------------
def test_signature_deposee_par_un_signataire_seulement(bn):
    with pytest.raises(s.CourrierRefuse):
        s.deposer_signature(bn["m1"].compte, image_signature())
    _signer(bn["president"].compte)
    _signer(bn["president"].compte)  # remplacement
    sigs = SignatureDeposee.objects.filter(compte=bn["president"].compte)
    assert sigs.count() == 2 and sigs.filter(active=True).count() == 1
    assert EntreeJournal.objects.filter(action="signature_deposee").count() == 2


def test_validation_par_le_president_avec_sa_signature(bn):
    c = _preparer(bn)
    pres = bn["president"].compte
    with pytest.raises(s.CourrierRefuse, match="signature"):
        s.valider(c, par=pres)  # pas encore de signature déposée
    _signer(pres)
    s.valider(c, par=pres)
    c.refresh_from_db()
    assert c.etat == Etat.ENVOYE
    assert c.numero == "001-2026/CCOSECS-CNC/AS/BNC/SN" or c.numero.startswith("001-")
    assert c.qualite == "titulaire" and c.fonction_signataire == "Président"
    assert c.signature.compte == pres and c.nom_signataire
    # Le responsable du bureau destinataire (Chef et Secrétaire de P1) est prévenu.
    assert Notification.objects.filter(destinataire=bn["sec_p1"].compte).exists()
    assert Notification.objects.filter(destinataire=bn["chef_p1"].compte).exists()
    assert not Notification.objects.filter(
        destinataire=bn["m1"].compte, message__startswith="Courrier"
    ).exists()
    assert EntreeJournal.objects.filter(action="courrier_envoye").exists()


def test_secretaire_national_signe_pour_ordre(bn):
    c = _preparer(bn)
    _signer(bn["sn"].compte)
    s.valider(c, par=bn["sn"].compte)
    c.refresh_from_db()
    assert c.qualite == "po" and c.fonction_signataire == "Secrétaire national"


def test_personne_d_autre_ne_signe(bn, compte_technique):
    c = _preparer(bn)
    for compte in (compte_technique, bn["chef_p1"].compte, bn["m1"].compte):
        with pytest.raises(s.CourrierRefuse):
            s.valider(c, par=compte)


def test_signature_inutilisable_apres_le_mandat(bn):
    import datetime

    from apps.bureaux.models import Mandat

    pres = bn["president"].compte
    _signer(pres)
    Mandat.objects.filter(membre=bn["president"]).update(date_fin=datetime.date(2025, 6, 1))
    with pytest.raises(s.CourrierRefuse):
        s.valider(_preparer(bn), par=pres)


def test_courrier_local_signe_par_le_chef(bn):
    c = s.preparer(
        unite=_p1(bn),
        nature="lettre",
        objet="Rapport",
        texte="T",
        bureaux=["national"],
        par=bn["sec_p1"].compte,
    )
    _signer(bn["chef_p1"].compte)
    s.valider(c, par=bn["chef_p1"].compte)
    c.refresh_from_db()
    assert c.qualite == "titulaire" and c.numero.endswith("/S")
    assert Notification.objects.filter(destinataire=bn["president"].compte).exists()


def test_renvoi_pour_correction_puis_modification(bn):
    c = _preparer(bn)
    _signer(bn["president"].compte)
    s.renvoyer(c, motif="Corriger la date", par=bn["president"].compte)
    c.refresh_from_db()
    assert c.etat == Etat.A_CORRIGER
    with pytest.raises(s.CourrierRefuse):
        s.valider(c, par=bn["president"].compte)
    s.modifier(c, objet="Nouvel objet", texte="Nouveau texte", par=bn["sn"].compte)
    c.refresh_from_db()
    assert c.etat == Etat.A_SIGNER and c.objet == "Nouvel objet"


def test_courrier_envoye_ne_se_modifie_plus(bn):
    c = _preparer(bn)
    _signer(bn["president"].compte)
    s.valider(c, par=bn["president"].compte)
    with pytest.raises(s.CourrierRefuse):
        s.modifier(c, objet="x", texte="y", par=bn["sn"].compte)
    with pytest.raises(s.CourrierRefuse):
        s.annuler(c, par=bn["sn"].compte)
    from django.core.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):
        c.delete()


# --- Accusés et transmission ---------------------------------------------------------------------
def _envoye(bn, **kw):
    c = _preparer(bn, **kw)
    _signer(bn["president"].compte)
    return s.valider(c, par=bn["president"].compte)


def test_accuses_reception_lecture_et_courrier_recu(bn):
    c = _envoye(bn)
    d = c.destinataires.get()
    sec = bn["sec_p1"].compte
    s.marquer_recus([d], sec)
    s.ouvrir(d, sec)
    s.accuser(d, par=sec)
    d.refresh_from_db()
    assert d.recu_le and d.lu_le and d.lu_par == sec and d.accuse_par == sec
    premier = d.lu_le
    s.ouvrir(d, bn["chef_p1"].compte)  # la première lecture reste
    d.refresh_from_db()
    assert d.lu_le == premier


def test_transmission_d_un_communique_aux_membres_de_la_paroisse(bn):
    c = _envoye(bn, nature="communique")
    s.transmettre_aux_membres(c, _p1(bn), par=bn["sec_p1"].compte)
    membres = Destinataire.objects.filter(courrier=c, type="membre")
    assert bn["m1"] in [d.membre for d in membres]
    assert all(d.transmis_par == f"paroisse-{bn['P1'].pk}" for d in membres)
    assert bn["m2"] not in [d.membre for d in membres]
    assert Notification.objects.filter(
        destinataire=bn["m1"].compte, message__startswith="Communiqué"
    ).exists()
    s.transmettre_aux_membres(c, _p1(bn), par=bn["sec_p1"].compte)  # sans doublon
    assert Destinataire.objects.filter(courrier=c, type="membre").count() == membres.count()


def test_transmission_refusee_hors_communique_ou_hors_destinataires(bn):
    lettre = _envoye(bn)
    with pytest.raises(s.CourrierRefuse):
        s.transmettre_aux_membres(lettre, _p1(bn), par=bn["sec_p1"].compte)
    communique = _envoye(bn, nature="communique", bureaux=[f"paroisse-{bn['P2'].pk}"])
    with pytest.raises(s.CourrierRefuse):
        s.transmettre_aux_membres(communique, _p1(bn), par=bn["sec_p1"].compte)


def test_membre_destinataire_direct(bn):
    c = _envoye(bn, bureaux=[], membres=[bn["m1"]])
    assert Notification.objects.filter(
        destinataire=bn["m1"].compte, message__startswith="Courrier"
    ).exists()
    assert list(s.courriers_du_membre(bn["m1"])) == [c]
    assert list(s.courriers_du_membre(bn["m2"])) == []


# --- Accès ---------------------------------------------------------------------------------------
def test_qui_peut_voir_un_courrier(bn, compte_technique):
    c = _preparer(bn)
    assert s.peut_voir(bn["sn"].compte, c)
    assert s.peut_voir(bn["president"].compte, c)
    assert not s.peut_voir(bn["sec_p1"].compte, c)  # pas encore envoyé
    _signer(bn["president"].compte)
    c = s.valider(c, par=bn["president"].compte)
    assert s.peut_voir(bn["sec_p1"].compte, c)
    assert not s.peut_voir(bn["m1"].compte, c)  # membre : seulement s'il est destinataire
    assert not s.peut_voir(bn["chef"].compte, c)  # le circuit n'est pas destinataire


# --- Clavier -------------------------------------------------------------------------------------
def test_mots_appris_seulement_goun_et_apres_deux_courriers(bn):
    texte = "Ẹ̀ jẹ́ mì wá gbọ́n. Mawu na yí wìdó. Adjovi sanction gbọ́n."
    _envoye(bn, texte=texte)
    mots = {m.mot: m for m in MotClavier.objects.all()}
    assert "gbọ́n" in mots and mots["gbọ́n"].nombre == 1  # une fois par courrier
    assert "mawu" not in mots and "sanction" not in mots  # français ou sans lettre goun
    assert "ẹ̀" not in mots  # écrit avec une majuscule : nom propre possible
    assert "gbọ́n" not in s.mots_suggeres()  # un seul courrier : pas encore proposé
    _envoye(bn, texte="gbọ́n wìdó", numero_ordre=2)
    assert "gbọ́n" in s.mots_suggeres() and "wìdó" in s.mots_suggeres()


def test_mots_du_bn_en_tete_et_mots_masques(bn):
    s.enregistrer_mots_bn("Akpé\nMawu\n", par=bn["sn"].compte)
    _envoye(bn, texte="wìdó wìdó")
    _envoye(bn, texte="wìdó", numero_ordre=2)
    assert s.mots_suggeres()[:2] == ["akpé", "mawu"]
    assert "wìdó" in s.mots_suggeres()
    s.masquer_mot("wìdó", par=bn["sn"].compte)
    assert "wìdó" not in s.mots_suggeres()


def test_signature_refusee_si_le_courrier_a_change(bn):
    c = _preparer(bn)
    _signer(bn["president"].compte)
    lu = c.version
    s.modifier(c, objet="Autre objet", texte="Autre texte", par=bn["sn"].compte)
    with pytest.raises(s.CourrierRefuse, match="modifié"):
        s.valider(c, par=bn["president"].compte, version=lu)
    c.refresh_from_db()
    s.valider(c, par=bn["president"].compte, version=c.version)


def test_changement_d_annee_entre_preparation_et_signature(bn):
    c = _preparer(bn)
    Courrier.objects.filter(pk=c.pk).update(annee=2025, numero_ordre=45)
    _signer(bn["president"].compte)
    c = s.valider(c, par=bn["president"].compte)
    assert c.annee == 2026 and c.numero.startswith("001-2026/")


def test_numero_pris_entre_temps_remplace_par_le_suivant(bn):
    a = _preparer(bn, numero_ordre=7)
    b = _preparer(bn, numero_ordre=8)
    Courrier.objects.filter(pk=b.pk).update(numero_ordre=7)
    _signer(bn["president"].compte)
    s.valider(a, par=bn["president"].compte)
    b = s.valider(b, par=bn["president"].compte)
    assert b.numero_ordre == 8


def test_noms_des_membres_destinataires_caches_aux_autres(bn):
    c = _envoye(bn, bureaux=[f"paroisse-{bn['P1'].pk}"], membres=[bn["m1"], bn["m4"]])
    complet = s.libelle_destinataires(c)
    assert bn["m4"].nom_complet in complet
    pour_m1 = s.libelle_destinataires(c, avec_membres=False, membre=bn["m1"])
    assert bn["m1"].nom_complet in pour_m1 and bn["m4"].nom_complet not in pour_m1
    assert "1 autre(s) membre(s)" in pour_m1
    pour_bureau = s.libelle_destinataires(c, avec_membres=False)
    assert bn["m1"].nom_complet not in pour_bureau and "2 membre(s)" in pour_bureau


def test_pdf_illisible_refuse_a_l_import(bn):
    faux = SimpleUploadedFile("x.pdf", b"%PDF-1.4\n garbage", content_type="application/pdf")
    with pytest.raises(s.CourrierRefuse, match="illisible"):
        _preparer(bn, mode="importe", texte="", fichier=faux)


def test_lettres_du_clavier_modifiables(bn):
    s.enregistrer_lettres("ẹ ọ ṣ ẹ", par=bn["sn"].compte)
    from apps.courrier.models import ReglagesClavier

    assert ReglagesClavier.courant().liste() == ["ẹ", "ọ", "ṣ"]
    assert Courrier.objects.count() == 0


def test_clavier_par_defaut_selon_la_liste_du_mainteneur(db):
    from apps.courrier.models import ReglagesClavier

    lettres = ReglagesClavier.courant().liste()
    assert lettres[:3] == ["ẹ", "ọ", "ṣ"]
    assert "◌́" in lettres and "◌̀" in lettres and "◌̃" in lettres


def test_ton_seul_enregistre_comme_touche_de_ton(bn):
    from apps.courrier.models import ReglagesClavier

    s.enregistrer_lettres("ẹ ́ ◌̀", par=bn["sn"].compte)
    assert ReglagesClavier.courant().liste() == ["ẹ", "◌́", "◌̀"]
