"""Identifiants d'un nouveau membre : encadré sur la fiche, bienvenue sans mot de passe."""

from django.core import mail
from django.utils import timezone

from apps.membres.models import Membre
from apps.membres.services import enregistrer_membre

DONNEES = {
    "nom": "Hounkpè",
    "prenoms": "Jean-Marc",
    "sexe": "M",
    "telephone": "0197000000",
    "categorie": "actif",
}


def test_encadre_identifiants_apres_enregistrement(client_bn, paroisse):
    r = client_bn.post(
        "/membres/bn/enregistrer/",
        {**DONNEES, "annee_integration": "2015", "paroisse_integration": paroisse.pk},
        follow=True,
    )
    html = r.content.decode()
    m = Membre.objects.get()
    assert "Identifiants à remettre" in html and m.matricule in html
    # Une fois le membre connecté, l'encadré disparaît.
    m.compte.last_login = timezone.now()
    m.compte.save(update_fields=["last_login"])
    html = client_bn.get(f"/membres/bn/{m.matricule}/").content.decode()
    assert "Identifiants à remettre" not in html


def test_email_bienvenue_sans_mot_de_passe(paroisse, compte_bn, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        res = enregistrer_membre(
            donnees=dict(DONNEES, email="jm@example.org"),
            paroisse_integration=paroisse,
            annee_integration=2015,
            par=compte_bn,
        )
    envoyes = [e for e in mail.outbox if "jm@example.org" in e.to]
    assert len(envoyes) == 1
    corps = envoyes[0].body
    assert res.membre.matricule in corps and "mot de passe provisoire" in corps
    assert res.mot_de_passe not in corps
    assert res.membre.compte.notifications.filter(message__contains="Bienvenue").exists()


def test_pas_de_bienvenue_pour_les_lots(paroisse, compte_bn, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        enregistrer_membre(
            donnees=dict(DONNEES, email="jm@example.org"),
            paroisse_integration=paroisse,
            annee_integration=2015,
            par=compte_bn,
            notifier=False,
            avec_mot_de_passe=False,
        )
    assert not mail.outbox
