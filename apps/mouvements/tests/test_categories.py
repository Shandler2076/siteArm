"""Catégories (13/11/2026) : exclusives ; seul passage sympathisant → actif, par le BNC."""

import datetime

import pytest
from django.test import Client
from django.utils import timezone

from apps.membres.models import Categorie, Membre


def test_les_bureaux_ne_signalent_plus_de_changement_de_categorie(monde):
    from apps.bureaux.perimetre import Unite
    from apps.mouvements.models import TypeSignalement
    from apps.mouvements.services import MouvementRefuse, signaler
    from apps.mouvements.views import types_permis

    unite = Unite("paroisse", monde["P1"])
    assert TypeSignalement.CATEGORIE not in types_permis(unite, monde["m1"])
    with pytest.raises(MouvementRefuse):
        signaler(
            membre=monde["m1"],
            type=TypeSignalement.CATEGORIE,
            par=monde["sec_p1"].compte,
            unite=unite.cle,
            nouvelle_categorie=Categorie.HONNEUR,
        )


def test_admettre_un_sympathisant_comme_actif(monde, compte_technique):
    from apps.mouvements.statuts import CategorieRefusee, admettre_comme_actif

    m1 = monde["m1"]
    with pytest.raises(CategorieRefusee):  # m1 est déjà actif
        admettre_comme_actif(
            m1, date_effet=timezone.localdate(), reference="D-3", motif="", par=compte_technique
        )
    Membre.objects.filter(pk=m1.pk).update(categorie=Categorie.SYMPATHISANT)
    m1.refresh_from_db()
    with pytest.raises(CategorieRefusee):  # référence obligatoire
        admettre_comme_actif(
            m1, date_effet=timezone.localdate(), reference="", motif="", par=compte_technique
        )
    h = admettre_comme_actif(
        m1,
        date_effet=datetime.date(2026, 11, 1),
        reference="D-3",
        motif="Admis",
        par=compte_technique,
    )
    m1.refresh_from_db()
    assert m1.categorie == Categorie.ACTIF and h.reference == "D-3"


def test_pages_bn_categorie(monde, client_technique):
    m1 = monde["m1"]
    Membre.objects.filter(pk=m1.pk).update(categorie=Categorie.SYMPATHISANT)
    html = client_technique.get(f"/membres/bn/{m1.matricule}/").content.decode()
    assert "Admettre comme membre actif" in html and "Corriger la catégorie" in html
    r = client_technique.post(
        f"/membres/bn/{m1.matricule}/categorie/",
        {"action": "admettre", "date_effet": "2026-11-01", "reference": "D-3", "motif": "Admis"},
    )
    assert r.status_code == 302
    m1.refresh_from_db()
    assert m1.categorie == Categorie.ACTIF
    r = client_technique.post(
        f"/membres/bn/{m1.matricule}/categorie/",
        {"action": "corriger", "categorie": "honneur", "motif": ""},
    )
    m1.refresh_from_db()
    assert m1.categorie == Categorie.ACTIF  # motif obligatoire
    client_technique.post(
        f"/membres/bn/{m1.matricule}/categorie/",
        {"action": "corriger", "categorie": "honneur", "motif": "Erreur de saisie"},
    )
    m1.refresh_from_db()
    assert m1.categorie == Categorie.HONNEUR
    c = Client()
    c.force_login(monde["sec_p1"].compte)
    assert (
        c.post(f"/membres/bn/{m1.matricule}/categorie/", {"action": "corriger"}).status_code == 403
    )
