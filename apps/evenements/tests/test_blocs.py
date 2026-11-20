"""Événements en quatre blocs (décisions du 20/11/2026) : bureau d'organisation et supervision
créés d'office, sections (chef de section puis membres), invitations d'honneur ; la qualité
imprimée sur l'autorisation vient du bloc."""

import datetime
import io
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone
from pypdf import PdfReader

from apps.evenements.models import POSTES_BUREAU_PAR_DEFAUT, Role
from apps.evenements.services import (
    EvenementRefuse,
    ajouter_poste_bureau,
    convoquer,
    creer_evenement,
)


@pytest.fixture
def ev(db, compte_technique):
    return creer_evenement(
        nom="Rassemblement",
        debut=timezone.now() + datetime.timedelta(days=3),
        lieu="Adjohoun",
        avec_autorisation=True,
        sessions=["Culte", "Accueil"],
        par=compte_technique,
    )


def _texte_pdf(c):
    from apps.evenements.pdf import autorisation_pdf

    return PdfReader(io.BytesIO(autorisation_pdf(c))).pages[0].extract_text()


def test_bureau_d_organisation_et_ses_postes(monde, ev, compte_technique):
    assert ev.postes_bureau == list(POSTES_BUREAU_PAR_DEFAUT)
    assert "Vice-président" in ev.postes_bureau and "Organisateur adjoint" in ev.postes_bureau
    ajouter_poste_bureau(ev, "Trésorier de l'événement", par=compte_technique)
    assert ev.postes_bureau[-1] == "Trésorier de l'événement"
    (c1,) = convoquer(
        ev, [monde["m1"]], role=Role.BUREAU_ORGANISATION, poste="Vice-président", par=None
    )
    assert c1.poste == "Vice-président" and c1.session is None
    # Un seul titulaire par poste : le nouveau prend le poste, l'ancien reste au bureau.
    convoquer(ev, [monde["m2"]], role=Role.BUREAU_ORGANISATION, poste="Vice-président", par=None)
    c1.refresh_from_db()
    assert c1.poste == "" and c1.role == Role.BUREAU_ORGANISATION
    with pytest.raises(EvenementRefuse):
        convoquer(ev, [monde["m3"]], role=Role.BUREAU_ORGANISATION, poste="Inconnu", par=None)


def test_un_seul_chef_par_section(monde, ev):
    culte = ev.sessions.get(nom="Culte")
    (a,) = convoquer(ev, [monde["m1"]], session=culte, role=Role.CHEF_SECTION, par=None)
    (b,) = convoquer(ev, [monde["m2"]], session=culte, role=Role.CHEF_SECTION, par=None)
    a.refresh_from_db()
    assert a.role == Role.TRAVAILLEUR and b.role == Role.CHEF_SECTION
    with pytest.raises(EvenementRefuse):
        convoquer(ev, [monde["m3"]], role=Role.CHEF_SECTION, par=None)  # sans section


@pytest.mark.parametrize(
    "role,section,qualite,precision",
    [
        (Role.SUPERVISEUR, False, "SUPERVISEUR", ""),
        (Role.BUREAU_ORGANISATION, False, "BUREAU D'ORGANISATION", "Organisateur"),
        (Role.TRAVAILLEUR, True, "MEMBRE TRAVAILLEUR", "Section Culte"),
        (Role.CHEF_SECTION, True, "CHEF DE SECTION", "Section Culte"),
        (Role.INVITE_HONNEUR, False, "INVITÉ(E) D'HONNEUR", ""),
        (Role.PARTICIPANT, False, "PARTICIPANT(E)", ""),
    ],
)
def test_qualite_imprimee_selon_le_bloc(monde, ev, role, section, qualite, precision):
    poste = "Organisateur" if role == Role.BUREAU_ORGANISATION else ""
    (c,) = convoquer(
        ev,
        [monde["m1"]],
        role=role,
        poste=poste,
        session=ev.sessions.get(nom="Culte") if section else None,
        par=None,
    )
    assert c.qualite_autorisation == qualite and c.precision_autorisation == precision
    texte = _texte_pdf(c)
    assert qualite in texte and "Est autorisé" not in texte and "AUTORISÉ" in texte


def test_en_tete_sans_le_texte_en_courbe():
    from apps.evenements import pdf
    from apps.membres.pdf import LOGO_CONGREGATION_SANS_TEXTE

    assert pdf.LOGO_EN_TETE == LOGO_CONGREGATION_SANS_TEXTE


def _client(compte):
    c = Client()
    c.force_login(compte)
    return c


def test_page_par_blocs(monde, ev, compte_technique):
    c = _client(compte_technique)
    culte = ev.sessions.get(nom="Culte")
    page = unescape(c.get(f"/evenements/{ev.pk}/convoquer/").content.decode())
    for onglet in (
        "Bureau d'organisation",
        "Supervision",
        "Culte",
        "Accueil",
        "Invitations d'honneur",
    ):
        assert onglet in page, onglet
    # Section : un chef et des membres, en une validation.
    url = f"/evenements/{ev.pk}/convoquer/?bloc=section-{culte.pk}"
    page = unescape(c.get(url).content.decode())
    assert "Chef de section" in page
    c.post(
        url,
        {
            "bloc": f"section-{culte.pk}",
            "membres": [monde["m1"].pk, monde["m2"].pk],
            "chef": monde["m1"].pk,
        },
    )
    roles = dict(ev.convocations.values_list("membre_id", "role"))
    assert roles[monde["m1"].pk] == Role.CHEF_SECTION and roles[monde["m2"].pk] == Role.TRAVAILLEUR
    # Bureau d'organisation : un poste par personne choisie.
    c.post(
        f"/evenements/{ev.pk}/convoquer/?bloc=bureau",
        {"bloc": "bureau", "membres": [monde["m3"].pk], f"poste_{monde['m3'].pk}": "Président"},
    )
    m3 = ev.convocations.get(membre=monde["m3"])
    assert m3.role == Role.BUREAU_ORGANISATION and m3.poste == "Président"
    page = unescape(c.get(f"/evenements/{ev.pk}/convoquer/?bloc=bureau").content.decode())
    assert "Président" in page and monde["m3"].nom_complet in page
    # La recherche signale la place actuelle (pour l'alerte « déjà placé »).
    r = c.get(f"/evenements/{ev.pk}/recherche-membres/", {"q": monde["m1"].matricule}).json()
    assert r["resultats"][0]["place"] == "Culte (chef de section)"
