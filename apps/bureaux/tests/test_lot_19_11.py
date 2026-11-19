"""Remarques du mainteneur du 19/11/2026 : échéances par bureau, bureaux en place, recherche
d'unité à l'installation, accueil du site dans le menu."""

import datetime
from html import unescape

from apps.bureaux.models import Mandat
from apps.bureaux.services import alertes_echeances
from apps.notifications.models import Notification


def _html(r):
    return unescape(r.content.decode())


def _bureau_p1_finit_le(monde, fin):
    """Le bureau de P1 (Secrétaire et Trésorier) finit à `fin` ; les autres finissent loin."""
    Mandat.objects.update(date_fin_prevue=datetime.date(2030, 1, 1))
    Mandat.objects.filter(paroisse=monde["P1"]).update(date_fin_prevue=fin)


def test_alerte_par_bureau_a_30_14_et_7_jours(monde):
    fin = datetime.date(2027, 1, 31)
    _bureau_p1_finit_le(monde, fin)
    sec = monde["sec_p1"].compte
    for jour, attendu in [
        (datetime.date(2026, 12, 31), 1),  # 31 jours : rien
        (datetime.date(2027, 1, 1), 1),  # 30 jours
        (datetime.date(2027, 1, 2), 0),
        (datetime.date(2027, 1, 17), 1),  # 14 jours
        (datetime.date(2027, 1, 24), 1),  # 7 jours
        (datetime.date(2027, 1, 25), 0),
    ]:
        avant = Notification.objects.filter(destinataire=sec).count()
        alertes_echeances(jour)
        recues = Notification.objects.filter(destinataire=sec).count() - avant
        assert recues == (0 if jour == datetime.date(2026, 12, 31) else attendu), jour
    messages = list(
        Notification.objects.filter(destinataire=sec, message__contains="bureau").values_list(
            "message", flat=True
        )
    )
    assert len(messages) == 3
    assert all("Le mandat du bureau de la Paroisse P1" in m for m in messages)
    assert all("Secrétaire paroissial" not in m for m in messages)  # le bureau, pas la personne


def test_un_seul_message_par_bureau_meme_avec_plusieurs_titulaires(monde):
    _bureau_p1_finit_le(monde, datetime.date(2027, 1, 31))
    alertes_echeances(datetime.date(2027, 1, 1))
    sec = monde["sec_p1"].compte
    assert Notification.objects.filter(destinataire=sec, message__contains="bureau").count() == 1


def test_bureau_echu_signale_une_fois(monde):
    _bureau_p1_finit_le(monde, datetime.date(2026, 11, 1))
    alertes_echeances(datetime.date(2026, 11, 10))
    alertes_echeances(datetime.date(2026, 11, 11))
    assert Notification.objects.filter(message__contains="est arrivé à échéance").count() >= 1
    sec = monde["sec_p1"].compte
    assert (
        Notification.objects.filter(destinataire=sec, message__contains="est arrivé").count() == 1
    )


def test_page_echeances_par_bureau(client_technique, monde):
    _bureau_p1_finit_le(monde, datetime.date.today() + datetime.timedelta(days=20))
    html = _html(client_technique.get("/bureau/bn/echeances/"))
    assert "Paroisse P1" in html and "Secrétaire paroissial" not in html
    assert html.count("Paroisse P1") == 1  # une ligne pour le bureau


def test_bureaux_en_place(client_technique, monde):
    html = _html(client_technique.get("/bureau/bn/bureaux/"))
    assert "HOULENOU" in html and "Ekpe A" in html and "P1" in html
    assert "Installé" in html and "Non installé" in html
    # Composition d'un bureau installé : matricule, noms, postes.
    html = _html(client_technique.get(f"/bureau/bn/bureaux/paroisse-{monde['P1'].pk}/"))
    assert monde["sec_p1"].matricule in html and "Secrétaire paroissial" in html


def test_bureaux_en_place_reserve_au_bn(client, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get("/bureau/bn/bureaux/").status_code == 403


def test_recherche_d_unite_a_l_installation(client_technique, territoire):
    html = _html(client_technique.get("/bureau/bn/installer/?niveau=paroisse"))
    assert 'data-filtre="choix-unite"' in html and 'id="choix-unite"' in html


def test_accueil_du_site_dans_le_menu_et_page_connecte(client_technique):
    html = _html(client_technique.get("/"))
    assert 'href="/site/"' in html and "Accueil du site" in html
    html = _html(client_technique.get("/site/"))
    assert "Vous êtes connecté" in html and "Ọmọ Ogun Igbala" in html
