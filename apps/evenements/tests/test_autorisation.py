import datetime
import io
from html import unescape

import pytest
from django.test import Client
from django.utils import timezone
from pypdf import PdfReader

from apps.evenements.services import annuler_evenement, convoquer, creer_evenement, retirer
from apps.membres.models import Membre


def _client(membre=None):
    c = Client()
    if membre is not None:
        c.force_login(membre.compte)
    return c


def _texte(contenu):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(contenu)).pages)


def _html(r):
    return unescape(r.content.decode())


@pytest.fixture
def ev(db, compte_technique):
    return creer_evenement(
        nom="Pèlerinage de la Nativité 2026",
        debut=timezone.make_aware(datetime.datetime(2026, 12, 24, 8, 0)),
        lieu="Porto-Novo",
        avec_autorisation=True,
        sessions=["Session Culte"],
        par=compte_technique,
    )


@pytest.fixture
def conv(monde, ev):
    Membre.objects.filter(pk=monde["m1"].pk).update(grade=5)
    (c,) = convoquer(ev, [monde["m1"]], session=ev.sessions.get(), par=None)
    return c


def test_mes_evenements_seulement_les_miens(monde, conv):
    html = _html(_client(monde["m1"]).get("/evenements/moi/"))
    assert "Pèlerinage de la Nativité 2026" in html and "Session Culte" in html
    assert "Mon autorisation" in html
    assert "Pèlerinage" not in _html(_client(monde["m2"]).get("/evenements/moi/"))


def test_autorisation_pdf_contenu(monde, conv):
    r = _client(monde["m1"]).get(f"/evenements/autorisation/{conv.pk}.pdf")
    texte = _texte(r.content)
    assert "Capitaine Test ADJOVI" in texte and monde["m1"].matricule in texte
    assert "autorisé(e) à travailler" in texte and "Session Culte" in texte
    assert "Pèlerinage de la Nativité 2026" in texte and "24/12/2026" in texte


def test_autorisation_sans_photo(monde, conv):
    texte = _texte(_client(monde["m1"]).get(f"/evenements/autorisation/{conv.pk}.pdf").content)
    assert "Photo à venir" in texte


def test_pas_d_autorisation_si_option_desactivee(monde, compte_technique):
    sans = creer_evenement(
        nom="Conclave", debut=timezone.now(), avec_autorisation=False, par=compte_technique
    )
    (c,) = convoquer(sans, [monde["m1"]], par=None)
    assert _client(monde["m1"]).get(f"/evenements/autorisation/{c.pk}.pdf").status_code == 404
    assert "Mon autorisation" not in _html(_client(monde["m1"]).get("/evenements/moi/"))


def test_autorisation_d_un_autre_404(monde, conv):
    assert _client(monde["m2"]).get(f"/evenements/autorisation/{conv.pk}.pdf").status_code == 404


def test_paroisse_imprime_l_autorisation_de_son_membre(monde, conv):
    c = _client(monde["sec_p1"])
    assert c.get(f"/evenements/autorisation/{conv.pk}.pdf").status_code == 200
    cle = f"paroisse-{monde['P1'].pk}"
    html = _html(c.get(f"/bureau/{cle}/membres/{monde['m1'].matricule}/"))
    assert f"/evenements/autorisation/{conv.pk}.pdf" in html


def test_circuit_et_region_ne_peuvent_pas_imprimer(monde, conv, donner_mandat):
    assert _client(monde["chef"]).get(f"/evenements/autorisation/{conv.pk}.pdf").status_code == 404
    donner_mandat(monde["m3"], "Secrétaire régional", monde["HOULENOU"])
    assert _client(monde["m3"]).get(f"/evenements/autorisation/{conv.pk}.pdf").status_code == 404
    cle = f"circuit-{monde['Ekpe A'].pk}"
    html = _html(_client(monde["chef"]).get(f"/bureau/{cle}/membres/{monde['m1'].matricule}/"))
    assert "autorisation" not in html.lower()


def test_autorisation_retiree_plus_telechargeable(monde, conv):
    retirer(conv, motif="Erreur", par=None)
    assert _client(monde["m1"]).get(f"/evenements/autorisation/{conv.pk}.pdf").status_code == 404


def test_verifier_valable_et_non_valable(monde, ev, conv):
    url = f"/evenements/verifier/{conv.jeton}/"
    html = _html(_client().get(url))
    assert "Autorisation valable" in html and "Capitaine Test ADJOVI" in html
    assert "Session Culte" in html
    retirer(conv, motif="Erreur", par=None)
    assert "Non valable" in _html(_client().get(url))
    assert "Non valable" in _html(_client().get("/evenements/verifier/invente123/"))


def test_verifier_evenement_annule(monde, ev, conv):
    annuler_evenement(ev, motif="Pluie", par=None)
    assert "Non valable" in _html(_client().get(f"/evenements/verifier/{conv.jeton}/"))


def test_verifier_ne_montre_ni_npi_ni_coordonnees(monde, conv):
    Membre.objects.filter(pk=monde["m1"].pk).update(npi="1234567890", quartier="Zongo")
    html = _html(_client().get(f"/evenements/verifier/{conv.jeton}/"))
    assert "1234567890" not in html and "0197000000" not in html and "Zongo" not in html


def test_historique_sur_la_fiche(monde, conv):
    html = _html(_client(monde["m1"]).get("/membres/ma-fiche/"))
    assert "Événements" in html and "Pèlerinage de la Nativité 2026" in html


def test_toutes_les_autorisations_bn(monde, conv, client_technique):
    r = client_technique.get(f"/evenements/{conv.evenement_id}/autorisations.pdf")
    assert r.status_code == 200 and "Test ADJOVI" in _texte(r.content)


def test_demo_evenements(territoire, settings):
    from django.core.management import call_command

    from apps.evenements.models import Evenement, Presence

    settings.SITE_DEMO = True
    call_command("peupler_demo", membres=60, stdout=io.StringIO())
    nativite = Evenement.objects.get(nom__startswith="Pèlerinage de la Nativité")
    assert nativite.avec_autorisation and nativite.sessions.count() == 3
    assert nativite.convocations.filter(active=True).count() >= 20
    conclave = Evenement.objects.get(nom__startswith="Conclave")
    assert not conclave.avec_autorisation
    assert conclave.convocations.filter(presence=Presence.PRESENT).exists()


@pytest.fixture(autouse=True)
def pendant_l_evenement(monkeypatch):
    """Le contrôle se fait pendant la période de validité (24/12/2026, 10 h)."""
    import apps.evenements.views as v

    monkeypatch.setattr(
        v, "maintenant", lambda: timezone.make_aware(datetime.datetime(2026, 12, 24, 10, 0))
    )
