import datetime

import pytest

from apps.bureaux.models import Fonction, Mandat
from apps.bureaux.perimetre import Unite, unites_gerees
from apps.bureaux.services import InstallationRefusee, installer_bureau
from apps.notifications.models import Notification

J = datetime.date(2026, 11, 10)


def test_installer_clot_l_ancien_bureau_et_notifie(
    territoire, nouveau_membre, donner_mandat, compte_technique, django_capture_on_commit_callbacks
):
    t = territoire
    ancien = nouveau_membre(t["P1"], "Ancien")
    donner_mandat(ancien, "Secrétaire paroissial", t["P1"], debut=datetime.date(2024, 1, 1))
    nouveau = nouveau_membre(t["P1"], "Nouveau")
    with django_capture_on_commit_callbacks(execute=True):
        mandats = installer_bureau(
            unite=Unite("paroisse", t["P1"]),
            titulaires={Fonction.objects.get(nom="Secrétaire paroissial"): nouveau},
            date_debut=J,
            par=compte_technique,
        )
    assert len(mandats) == 1 and mandats[0].installe_par == compte_technique
    assert unites_gerees(ancien.compte, J) == []
    assert [u.objet for u in unites_gerees(nouveau.compte, J)] == [t["P1"]]
    assert Mandat.objects.get(membre=ancien).date_fin == J
    assert Notification.objects.filter(
        destinataire=ancien.compte, message__contains="a pris fin"
    ).exists()
    assert Notification.objects.filter(
        destinataire=nouveau.compte, message__contains="installé"
    ).exists()


def test_titulaire_non_actif_refuse(territoire, nouveau_membre, compte_technique):
    m = nouveau_membre(territoire["P1"], "Exclu")
    m.statut = "exclu"
    m.save()
    with pytest.raises(InstallationRefusee, match="pas un membre actif"):
        installer_bureau(
            unite=Unite("paroisse", territoire["P1"]),
            titulaires={Fonction.objects.get(nom="Secrétaire paroissial"): m},
            date_debut=J,
            par=compte_technique,
        )
    assert not Mandat.objects.exists()


def test_fonction_d_un_autre_niveau_refusee(territoire, nouveau_membre, compte_technique):
    m = nouveau_membre(territoire["P1"], "X")
    with pytest.raises(InstallationRefusee):
        installer_bureau(
            unite=Unite("paroisse", territoire["P1"]),
            titulaires={Fonction.objects.get(nom="Président"): m},
            date_debut=J,
            par=compte_technique,
        )


def test_page_installer_reservee_au_bn(client, territoire, nouveau_membre):
    client.force_login(nouveau_membre(territoire["P1"], "X").compte)
    assert client.get("/bureau/bn/installer/").status_code == 403


def test_page_installer_par_matricule(client_technique, territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Chef")
    f = Fonction.objects.get(nom="Chef d'Unité paroissiale")
    base = {"niveau": "paroisse", "unite": territoire["P1"].pk, "date_debut": "2026-11-10"}
    r = client_technique.get(
        "/bureau/bn/installer/", {"niveau": "paroisse", "unite": territoire["P1"].pk}
    )
    assert "Chef d&#x27;Unité paroissiale" in r.content.decode()
    r = client_technique.post(
        "/bureau/bn/installer/", {**base, f"fonction_{f.pk}": m.matricule.lower()}
    )
    assert r.status_code == 302 and Mandat.objects.filter(membre=m, fonction=f).exists()
    r = client_technique.post(
        "/bureau/bn/installer/", {**base, f"fonction_{f.pk}": "2099-99AS-9999"}
    )
    assert "Matricule inconnu : 2099-99AS-9999" in r.content.decode()


def test_accorder_le_droit_de_gerer(client_technique):
    f = Fonction.objects.get(nom="Trésorier paroissial")
    r = client_technique.post("/bureau/bn/fonctions/", {"fonction": f.pk, "droit_gerer": "on"})
    assert r.status_code == 302
    f.refresh_from_db()
    assert f.droit_gerer
    client_technique.post("/bureau/bn/fonctions/", {"fonction": f.pk})
    f.refresh_from_db()
    assert not f.droit_gerer


def test_page_fonctions_reservee_au_bn(client, territoire, nouveau_membre):
    client.force_login(nouveau_membre(territoire["P1"], "X").compte)
    assert client.get("/bureau/bn/fonctions/").status_code == 403
