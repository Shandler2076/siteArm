"""« Vérifier un membre » hors de son périmètre (décision du 13/11/2026)."""

from html import unescape

import pytest
from django.test import Client

from apps.journal.models import EntreeJournal

URL = "/bureau/verifier/"


@pytest.fixture
def scene(monde, nouveau_membre, donner_mandat):
    t = monde
    sec_p4 = nouveau_membre(t["P4"], "SecWeme")
    donner_mandat(sec_p4, "Secrétaire paroissial", t["P4"])
    tres_p4 = nouveau_membre(t["P4"], "TresWeme")
    donner_mandat(tres_p4, "Trésorier paroissial", t["P4"])
    return dict(t, sec_p4=sec_p4, tres_p4=tres_p4)


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def test_secretaire_verifie_un_membre_d_ailleurs(scene):
    c = _client(scene["sec_p4"])  # Secrétaire d'une paroisse de WEME
    m1 = scene["m1"]  # membre de P1 (HOULENOU) : hors de son périmètre
    r = c.post(URL, {"matricule": m1.matricule, "motif": "visite"})
    html = unescape(r.content.decode())
    assert r.status_code == 200
    assert m1.nom_complet in html and "P1" in html and "Actif" in html
    # Le contact de sa paroisse : le Secrétaire paroissial de P1.
    assert scene["sec_p1"].nom_complet in html
    # Jamais le téléphone du membre ni son NPI.
    assert "0197000000" not in html.replace(scene["sec_p1"].telephone, "")
    e = EntreeJournal.objects.filter(action="verification_membre").latest("pk")
    assert e.details["membre"] == m1.matricule and e.details["motif"] == "visite"


def test_motif_obligatoire_et_autre_a_preciser(scene):
    c = _client(scene["sec_p4"])
    m1 = scene["m1"]
    html = unescape(c.post(URL, {"matricule": m1.matricule}).content.decode())
    assert m1.nom_complet not in html
    html = unescape(c.post(URL, {"matricule": m1.matricule, "motif": "autre"}).content.decode())
    assert m1.nom_complet not in html and "Précisez le motif" in html
    html = unescape(
        c.post(
            URL, {"matricule": m1.matricule, "motif": "autre", "precision": "Baptême"}
        ).content.decode()
    )
    assert m1.nom_complet in html


def test_pas_de_recherche_par_nom(scene):
    c = _client(scene["sec_p4"])
    html = unescape(c.post(URL, {"matricule": "ADJOVI", "motif": "visite"}).content.decode())
    assert "Aucun membre ne porte ce matricule" in html
    assert scene["m1"].nom_complet not in html


@pytest.mark.parametrize("qui", ["tres_p4", "m1"])
def test_reserve_au_chef_et_au_secretaire(scene, qui):
    c = _client(scene[qui])
    assert c.get(URL).status_code == 403
    r = c.post(URL, {"matricule": scene["m2"].matricule, "motif": "visite"})
    assert r.status_code == 403


def test_chef_de_circuit_peut_verifier(scene):
    c = _client(scene["chef"])
    r = c.post(URL, {"matricule": scene["m4"].matricule, "motif": "faute"})
    assert scene["m4"].nom_complet in unescape(r.content.decode())


def test_lien_dans_le_menu(scene):
    from django.test import RequestFactory

    from apps.bureaux.menu import construire_menu

    req = RequestFactory().get("/")
    req.user = scene["sec_p4"].compte
    libelles = [lien.libelle for g in construire_menu(req) for lien in g.liens]
    assert "Vérifier un membre" in libelles
    req.user = scene["tres_p4"].compte
    libelles = [lien.libelle for g in construire_menu(req) for lien in g.liens]
    assert "Vérifier un membre" not in libelles


def test_fonctions_sous_la_photo(scene, donner_mandat):
    """Demande du 20/11/2026 : les fonctions en cours de la personne, sous sa photo."""
    import datetime

    t = scene
    m1 = t["m1"]
    donner_mandat(m1, "Trésorier national")
    donner_mandat(m1, "Président")
    donner_mandat(m1, "Chef de Section de Circuit", t["C1"] if "C1" in t else t["P1"].circuit)
    # Un mandat terminé n'apparaît pas.
    donner_mandat(m1, "Secrétaire paroissial", t["P1"], fin=datetime.date(2025, 6, 1))
    c = _client(t["sec_p4"])
    html = unescape(c.post(URL, {"matricule": m1.matricule, "motif": "visite"}).content.decode())
    assert 'class="carte-identite__fonctions"' in html
    assert "Trésorier national" in html
    assert "Président — Bureau National de Commandement" in html
    circuit = t["P1"].circuit.nom
    assert f"Chef de Section de Circuit — {circuit}" in html
    assert f"Secrétaire paroissial — {t['P1'].nom}" not in html


def test_sans_fonction_rien_sous_la_photo(scene):
    c = _client(scene["sec_p4"])
    m2 = scene["m2"]
    html = unescape(c.post(URL, {"matricule": m2.matricule, "motif": "visite"}).content.decode())
    assert m2.nom_complet in html
    assert 'class="carte-identite__fonctions"' not in html
