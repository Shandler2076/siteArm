import datetime

from django.core import mail

from apps.notifications.models import Notification
from apps.notifications.services import notifier


def test_notifier_sans_doublon_et_email(territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Mail")
    m.email = "m@exemple.bj"
    m.save()
    assert notifier([m.compte, m.compte], "Bonjour", "/x/") == 1
    assert mail.outbox[0].to == ["m@exemple.bj"] and "Bonjour" in mail.outbox[0].body


def test_pas_de_notification_aux_comptes_inactifs(territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Inactif")
    m.compte.is_active = False
    m.compte.save()
    assert notifier([m.compte], "Bonjour") == 0


def test_nouveau_membre_notifie_les_trois_bureaux(
    territoire, nouveau_membre, donner_mandat, django_capture_on_commit_callbacks
):
    t = territoire
    d = datetime.date(2025, 1, 1)
    sp = nouveau_membre(t["P1"], "SecP")
    donner_mandat(sp, "Secrétaire paroissial", t["P1"], debut=d)
    sc = nouveau_membre(t["P1"], "SecC")
    donner_mandat(sc, "Secrétaire de Circuit", t["Ekpe A"], debut=d)
    sr = nouveau_membre(t["P1"], "SecR")
    donner_mandat(sr, "Secrétaire régional", t["HOULENOU"], debut=d)
    autre = nouveau_membre(t["P4"], "SecW")
    donner_mandat(autre, "Secrétaire paroissial", t["P4"], debut=d)
    with django_capture_on_commit_callbacks(execute=True):
        nouveau = nouveau_membre(t["P1"], "Nouveau")
    for titulaire in (sp, sc, sr):
        n = Notification.objects.get(destinataire=titulaire.compte)
        assert n.message == (
            f"Nouveau membre dans votre périmètre : {nouveau.matricule} — {nouveau.nom_complet}"
        )
    assert not Notification.objects.filter(destinataire=autre.compte).exists()


def test_page_marque_comme_lu(client, territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Lecteur")
    notifier([m.compte], "Message A", "/membres/ma-fiche/")
    client.force_login(m.compte)
    assert 'class="cloche__nombre">1<' in client.get("/").content.decode()
    html = client.get("/notifications/").content.decode()
    assert "Message A" in html and "/membres/ma-fiche/" in html
    assert not Notification.objects.filter(lue=False).exists()
    assert 'class="cloche__nombre"' not in client.get("/").content.decode()
