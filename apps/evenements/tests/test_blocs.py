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


# --- Relecture du 20/11/2026 -------------------------------------------------------------------
def test_anciennes_convocations_hors_section_restent_visibles(monde, ev, compte_technique):
    """Un « officiel » sans section dans un événement à sections apparaît encore au détail."""
    from apps.evenements.blocs import blocs

    convoquer(ev, [monde["m1"]], role=Role.OFFICIEL, par=None)
    page = unescape(_client(compte_technique).get(f"/evenements/{ev.pk}/").content.decode())
    assert monde["m1"].nom_complet in page
    assert any(b["nombre"] == 1 and b["cle"] == "participants" for b in blocs(ev))


def test_membre_sans_section_reste_visible_dans_participants(monde, ev):
    """Ancien usage : un membre sans section dans un événement à sections reste visible."""
    from apps.evenements.blocs import blocs

    convoquer(ev, [monde["m1"]], par=None)
    assert [b["nombre"] for b in blocs(ev) if b["cle"] == "participants"] == [1]


def test_validation_tout_ou_rien(monde, ev, compte_technique):
    from apps.mouvements.statuts import changer_statut

    changer_statut(
        monde["m4"], "exclu", par=compte_technique, date_effet=datetime.date.today(), motif="t"
    )
    culte = ev.sessions.get(nom="Culte")
    c = _client(compte_technique)
    c.post(
        f"/evenements/{ev.pk}/convoquer/",
        {
            "bloc": f"section-{culte.pk}",
            "membres": [monde["m1"].pk, monde["m4"].pk],
            "chef": monde["m1"].pk,
        },
    )
    assert not ev.convocations.exists()


def test_meme_poste_pour_deux_personnes_refuse(monde, ev, compte_technique):
    c = _client(compte_technique)
    c.post(
        f"/evenements/{ev.pk}/convoquer/",
        {
            "bloc": "bureau",
            "membres": [monde["m1"].pk, monde["m2"].pk],
            f"poste_{monde['m1'].pk}": "Président",
            f"poste_{monde['m2'].pk}": "Président",
        },
    )
    assert not ev.convocations.exists()


def test_bloc_inconnu_et_retrait_non_numerique(monde, ev, compte_technique):
    c = _client(compte_technique)
    r = c.post(
        f"/evenements/{ev.pk}/convoquer/", {"bloc": "participants", "membres": [monde["m1"].pk]}
    )
    assert r.status_code == 302 and not ev.convocations.exists()  # pas de repli sur le bureau
    r = c.post(
        f"/evenements/{ev.pk}/convoquer/",
        {"bloc": "bureau", "action": "retirer", "convocation": "abc"},
    )
    assert r.status_code == 404


def test_poste_bureau_doublon_casse_et_evenement_annule(ev, compte_technique):
    from apps.evenements.services import annuler_evenement

    with pytest.raises(EvenementRefuse):
        ajouter_poste_bureau(ev, "président", par=compte_technique)
    annuler_evenement(ev, motif="Pluie", par=compte_technique)
    with pytest.raises(EvenementRefuse):
        ajouter_poste_bureau(ev, "Trésorier", par=compte_technique)


def test_retrait_refuse_si_evenement_annule(monde, ev, compte_technique):
    from apps.evenements.services import annuler_evenement, retirer

    (c,) = convoquer(ev, [monde["m1"]], role=Role.SUPERVISEUR, par=None)
    annuler_evenement(ev, motif="Pluie", par=compte_technique)
    with pytest.raises(EvenementRefuse):
        retirer(c, motif="Erreur", par=compte_technique)


def test_deplacements_entre_blocs(monde, ev):
    culte = ev.sessions.get(nom="Culte")
    (c,) = convoquer(ev, [monde["m1"]], role=Role.BUREAU_ORGANISATION, poste="Président", par=None)
    convoquer(ev, [monde["m1"]], session=culte, role=Role.CHEF_SECTION, par=None)
    c.refresh_from_db()
    assert c.poste == "" and c.session == culte and c.role == Role.CHEF_SECTION
    convoquer(ev, [monde["m1"]], role=Role.SUPERVISEUR, par=None)
    c.refresh_from_db()
    assert c.session is None and c.role == Role.SUPERVISEUR
    assert ev.convocations.filter(active=True).count() == 1


def test_recherche_donne_la_cle_du_bloc_et_le_poste(monde, ev, compte_technique):
    convoquer(ev, [monde["m1"]], role=Role.BUREAU_ORGANISATION, poste="Secrétaire", par=None)
    r = (
        _client(compte_technique)
        .get(f"/evenements/{ev.pk}/recherche-membres/", {"q": monde["m1"].matricule})
        .json()["resultats"][0]
    )
    assert r["bloc"] == "bureau" and r["poste"] == "Secrétaire"


def test_qualite_tres_longue_reste_lisible(monde, ev):
    (c,) = convoquer(ev, [monde["m1"]], role=Role.AUTRE, role_autre="Protocole " * 9, par=None)
    texte = _texte_pdf(c)
    assert "PROTOCOLE" in texte


def test_en_tete_comme_les_courriers(monde, ev):
    """Remarque du 20/11/2026 : entre les deux logos, la Congrégation, le Comité National de
    Coordination et le Bureau National de Commandement, alignés comme sur les courriers."""
    (c,) = convoquer(ev, [monde["m1"]], role=Role.SUPERVISEUR, par=None)
    texte = _texte_pdf(c)
    for ligne in (
        "CONGRÉGATION CHRÉTIENNE DE L'ORDRE SACRÉ ÉTERNEL",
        "DES CHÉRUBINS ET SÉRAPHINS",
        "COMITÉ NATIONAL DE COORDINATION",
        "BUREAU NATIONAL DE COMMANDEMENT",
        "AUTORISATION",
    ):
        assert ligne in texte, ligne
