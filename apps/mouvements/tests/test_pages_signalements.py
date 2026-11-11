from datetime import date, timedelta
from html import unescape

from django.utils import timezone

from apps.mouvements.models import Signalement
from apps.mouvements.statuts import changer_statut


def _fiche(monde, niveau, nom, membre):
    return f"/bureau/{niveau}-{monde[nom].pk}/membres/{membre.matricule}/"


def test_boutons_selon_niveau(client, monde):
    m1 = monde["m1"]
    client.force_login(monde["sec_p1"].compte)
    html = client.get(_fiche(monde, "paroisse", "P1", m1)).content.decode()
    for t in ("deces", "demission", "categorie"):
        assert f"signaler/{t}/" in html
    assert "signaler/rehabilitation/" not in html
    client.force_login(monde["chef"].compte)
    html = client.get(_fiche(monde, "circuit", "Ekpe A", m1)).content.decode()
    assert "signaler/categorie/" in html and "signaler/deces/" not in html


def test_signaler_deces(client, monde):
    m1 = monde["m1"]
    client.force_login(monde["sec_p1"].compte)
    url = _fiche(monde, "paroisse", "P1", m1) + "signaler/deces/"
    assert client.get(url).status_code == 200
    r = client.post(url, {"date_effet": "2026-11-01", "commentaire": "Annoncé dimanche"})
    assert r.status_code == 302
    sig = Signalement.objects.get()
    assert sig.type == "deces" and sig.date_effet == date(2026, 11, 1)
    assert sig.unite == f"paroisse-{monde['P1'].pk}"
    html = unescape(client.get(r.url).content.decode())
    assert "Signalement transmis au Bureau national." in html and "En attente du BN" in html


def test_signaler_hors_perimetre_404(client, monde):
    client.force_login(monde["sec_p1"].compte)
    url = _fiche(monde, "paroisse", "P1", monde["m2"]) + "signaler/deces/"
    assert client.post(url, {"date_effet": "2026-11-01"}).status_code == 404
    client.force_login(monde["chef"].compte)
    url = _fiche(monde, "circuit", "Ekpe A", monde["m1"]) + "signaler/deces/"
    assert client.post(url, {"date_effet": "2026-11-01"}).status_code == 404
    url = _fiche(monde, "paroisse", "P1", monde["m1"]) + "signaler/inconnu/"
    assert client.get(url).status_code == 404
    assert not Signalement.objects.exists()


def test_rehabilitation_bloquee_affiche_raison(client, monde):
    m1 = monde["m1"]
    changer_statut(
        m1,
        "demissionnaire",
        par=None,
        date_effet=timezone.localdate() - timedelta(days=30),
        motif="Démission",
    )
    client.force_login(monde["sec_p1"].compte)
    html = client.get(_fiche(monde, "paroisse", "P1", m1)).content.decode()
    assert "Réhabilitation possible à partir du" in html
    assert "signaler/rehabilitation/" not in html
    assert "signaler/deces/" not in html


def test_rehabilitation_possible_bouton(client, monde):
    m1 = monde["m1"]
    changer_statut(m1, "demissionnaire", par=None, date_effet=date(2025, 1, 1), motif="Démission")
    client.force_login(monde["sec_p1"].compte)
    html = client.get(_fiche(monde, "paroisse", "P1", m1)).content.decode()
    assert "signaler/rehabilitation/" in html


def test_erreurs_formulaire(client, monde):
    client.force_login(monde["sec_p1"].compte)
    url = _fiche(monde, "paroisse", "P1", monde["m1"]) + "signaler/deces/"
    futur = (timezone.localdate() + timedelta(days=3)).isoformat()
    r = client.post(url, {"date_effet": futur})
    assert r.status_code == 200 and "futur" in r.content.decode()
    r = client.post(url, {})
    assert r.status_code == 200
    assert not Signalement.objects.exists()


def test_categorie_choix_sans_actuelle(client, monde):
    client.force_login(monde["chef"].compte)
    url = _fiche(monde, "circuit", "Ekpe A", monde["m1"]) + "signaler/categorie/"
    html = client.get(url).content.decode()
    assert 'value="honneur"' in html and 'value="actif"' not in html
    r = client.post(url, {"nouvelle_categorie": "honneur"})
    assert r.status_code == 302 and Signalement.objects.get().nouvelle_categorie == "honneur"
