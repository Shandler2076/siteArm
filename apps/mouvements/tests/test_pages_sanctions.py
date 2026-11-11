from datetime import date, timedelta
from html import unescape

from django.utils import timezone

from apps.mouvements.models import Sanction
from apps.mouvements.sanctions import enregistrer_sanction


def _url(m):
    return f"/bureau/bn/sanctions/{m.matricule}/nouvelle/"


def test_sanction_reservee_au_bn(client, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get(_url(monde["m1"])).status_code == 403
    assert client.post(_url(monde["m1"]), {"type": "blame"}).status_code == 403
    assert not Sanction.objects.exists()


def test_formulaire_sanction(client_technique, monde):
    m1 = monde["m1"]
    page = client_technique.get(f"/membres/bn/{m1.matricule}/").content.decode()
    assert _url(m1) in page
    aujourdhui = timezone.localdate()
    r = client_technique.post(
        _url(m1),
        {
            "degre": "2",
            "type": "suspension",
            "date_debut": aujourdhui.isoformat(),
            "date_fin": (aujourdhui + timedelta(days=10)).isoformat(),
            "motif": "Absences répétées",
            "reference": "Décision BNC n° 12",
        },
    )
    assert r.status_code == 302 and r.url == f"/membres/bn/{m1.matricule}/"
    m1.refresh_from_db()
    assert m1.statut == "sanctionne" and Sanction.objects.get().degre == 2
    r = client_technique.post(
        _url(m1),
        {
            "degre": "1",
            "type": "suspension",
            "date_debut": aujourdhui.isoformat(),
            "date_fin": (aujourdhui + timedelta(days=30)).isoformat(),
            "motif": "x",
            "reference": "y",
        },
    )
    assert r.status_code == 200 and "15 jours" in unescape(r.content.decode())
    assert Sanction.objects.count() == 1


def test_sanctions_visibles_membre_bureaux_bn(client, client_technique, monde, compte_technique):
    m1 = monde["m1"]
    enregistrer_sanction(
        membre=m1,
        degre=1,
        type="blame",
        date_debut=date(2026, 11, 1),
        motif="Retard",
        reference="Décision n° 3",
        par=compte_technique,
    )
    pages = [client_technique.get(f"/membres/bn/{m1.matricule}/")]
    client.force_login(monde["sec_p1"].compte)
    pages.append(client.get(f"/bureau/paroisse-{monde['P1'].pk}/membres/{m1.matricule}/"))
    client.force_login(monde["chef"].compte)
    pages.append(client.get(f"/bureau/circuit-{monde['Ekpe A'].pk}/membres/{m1.matricule}/"))
    client.force_login(m1.compte)
    pages.append(client.get("/membres/ma-fiche/"))
    for r in pages:
        html = unescape(r.content.decode())
        assert "Sanctions" in html and "Blâme écrit" in html and "Décision n° 3" in html
    client.force_login(monde["m2"].compte)
    assert "Blâme écrit" not in client.get("/membres/ma-fiche/").content.decode()


def test_lever_depuis_la_fiche(client_technique, monde, compte_technique):
    m1 = monde["m1"]
    s = enregistrer_sanction(
        membre=m1,
        degre=3,
        type="exclusion_definitive",
        date_debut=date(2026, 11, 1),
        motif="Faute grave",
        reference="D-1",
        par=compte_technique,
    )
    page = client_technique.get(f"/membres/bn/{m1.matricule}/").content.decode()
    assert f"/bureau/bn/sanctions/{s.pk}/lever/" in page
    r = client_technique.post(f"/bureau/bn/sanctions/{s.pk}/lever/", {"motif_levee": ""})
    assert r.status_code == 302
    s.refresh_from_db()
    assert s.levee_le is None
    client_technique.post(f"/bureau/bn/sanctions/{s.pk}/lever/", {"motif_levee": "Erreur"})
    s.refresh_from_db()
    m1.refresh_from_db()
    assert s.levee_le is not None and m1.statut == "actif"
    html = unescape(client_technique.get(f"/membres/bn/{m1.matricule}/").content.decode())
    assert "Levée le" in html
