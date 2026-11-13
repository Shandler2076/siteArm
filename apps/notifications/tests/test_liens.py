"""Notifications qui mènent à la bonne page (décision du 13/11/2026)."""

import datetime

import pytest
from django.test import Client

from apps.notifications.models import Notification
from apps.notifications.services import notifier, resoudre_lien


@pytest.fixture
def scene(territoire, nouveau_membre, donner_mandat):
    t = territoire
    m1 = nouveau_membre(t["P1"], "Adjovi")
    sec_p1 = nouveau_membre(t["P1"], "Secretaire")
    donner_mandat(sec_p1, "Secrétaire paroissial", t["P1"], debut=datetime.date(2025, 1, 1))
    sec_p4 = nouveau_membre(t["P4"], "Autre")
    donner_mandat(sec_p4, "Secrétaire paroissial", t["P4"], debut=datetime.date(2025, 1, 1))
    return dict(t, m1=m1, sec_p1=sec_p1, sec_p4=sec_p4)


def test_lien_membre_selon_le_destinataire(scene, compte_technique):
    m1, cible = scene["m1"], f"membre:{scene['m1'].matricule}"
    assert resoudre_lien(m1.compte, cible) == "/membres/ma-fiche/"
    assert resoudre_lien(scene["sec_p1"].compte, cible) == (
        f"/bureau/paroisse-{scene['P1'].pk}/membres/{m1.matricule}/"
    )
    assert resoudre_lien(compte_technique, cible) == f"/membres/bn/{m1.matricule}/"
    # Hors périmètre : pas de lien (le gardien des périmètres décide).
    assert resoudre_lien(scene["sec_p4"].compte, cible) is None
    assert resoudre_lien(m1.compte, "/cotisations/moi/") == "/cotisations/moi/"
    assert resoudre_lien(m1.compte, "https://exemple.org/") is None


def test_clic_marque_lue_et_redirige(scene):
    m1 = scene["m1"]
    notifier([m1.compte], "Votre cotisation est validée.", "/cotisations/moi/")
    n = Notification.objects.get(destinataire=m1.compte)
    c = Client()
    c.force_login(m1.compte)
    html = c.get("/notifications/").content.decode()
    assert f"/notifications/{n.pk}/" in html
    n.refresh_from_db()
    assert not n.lue  # la liste seule ne marque plus tout comme lu
    r = c.get(f"/notifications/{n.pk}/")
    assert r.status_code == 302 and r.url == "/cotisations/moi/"
    n.refresh_from_db()
    assert n.lue


def test_notification_d_un_autre_404(scene):
    notifier([scene["m1"].compte], "Info", "/cotisations/moi/")
    n = Notification.objects.get()
    c = Client()
    c.force_login(scene["sec_p1"].compte)
    assert c.get(f"/notifications/{n.pk}/").status_code == 404


def test_tout_marquer_comme_lu(scene):
    notifier([scene["m1"].compte], "A")
    notifier([scene["m1"].compte], "B")
    c = Client()
    c.force_login(scene["m1"].compte)
    c.post("/notifications/tout-lu/")
    assert not Notification.objects.filter(lue=False).exists()


def test_convocation_mene_a_mes_evenements(
    scene, compte_technique, django_capture_on_commit_callbacks
):
    from django.utils import timezone

    from apps.evenements.services import convoquer, creer_evenement

    ev = creer_evenement(
        nom="Conclave", debut=timezone.now() + datetime.timedelta(days=3), par=compte_technique
    )
    with django_capture_on_commit_callbacks(execute=True):
        convoquer(ev, [scene["m1"]], par=compte_technique)
    n = Notification.objects.get(destinataire=scene["m1"].compte)
    assert n.lien == f"/evenements/moi/#ev{ev.pk}"


def test_nouveau_membre_mene_a_sa_fiche(
    scene, compte_technique, django_capture_on_commit_callbacks
):
    from apps.membres.services import enregistrer_membre

    with django_capture_on_commit_callbacks(execute=True):
        m = enregistrer_membre(
            donnees={
                "nom": "Nouveau",
                "prenoms": "X",
                "sexe": "M",
                "telephone": "0197000000",
                "categorie": "actif",
            },
            paroisse_integration=scene["P1"],
            annee_integration=2015,
            par=compte_technique,
        ).membre
    n = Notification.objects.filter(destinataire=scene["sec_p1"].compte).latest("pk")
    assert n.lien == f"membre:{m.matricule}"
    bienvenue = Notification.objects.get(destinataire=m.compte)
    assert bienvenue.lien == "/membres/ma-fiche/"
