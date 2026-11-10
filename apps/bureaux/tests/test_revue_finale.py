"""Corrections issues de la relecture finale de l'étape 3."""

import datetime
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.bureaux.models import Fonction, Mandat
from apps.bureaux.perimetre import Unite
from apps.bureaux.services import InstallationRefusee, alertes_echeances, installer_bureau
from apps.notifications.models import Notification


def _reset(client, monde, cible):
    client.force_login(monde["sec_p1"].compte)
    return client.post(
        f"/bureau/paroisse-{monde['P1'].pk}/membres/{cible.matricule}/reinitialiser/"
    )


# C1 — une paroisse ne réinitialise jamais un compte qui a des droits particuliers
def test_reset_refuse_sur_compte_avec_autorisation_manuelle(client, monde):
    from django.contrib.auth.models import Permission

    cible = monde["m1"]
    cible.compte.user_permissions.add(Permission.objects.get(codename="gerer_membres"))
    avant = cible.compte.password
    assert _reset(client, monde, cible).status_code == 403
    cible.compte.refresh_from_db()
    assert cible.compte.password == avant


def test_reset_refuse_sur_compte_de_gestion(client, monde):
    cible = monde["m1"]
    cible.compte.is_staff = True
    cible.compte.save()
    assert _reset(client, monde, cible).status_code == 403


# I2 — installation antidatée : refusée, l'histoire n'est pas réécrite
def test_installation_antidatee_refusee(territoire, nouveau_membre, compte_technique):
    t = territoire
    sec = Fonction.objects.get(nom="Secrétaire paroissial")
    a, b = nouveau_membre(t["P1"], "Adjovi"), nouveau_membre(t["P1"], "Bio")
    installer_bureau(
        unite=Unite("paroisse", t["P1"]),
        titulaires={sec: a},
        date_debut=datetime.date(2026, 3, 1),
        par=compte_technique,
    )
    with pytest.raises(InstallationRefusee, match="plus récent"):
        installer_bureau(
            unite=Unite("paroisse", t["P1"]),
            titulaires={sec: b},
            date_debut=datetime.date(2026, 1, 1),
            par=compte_technique,
        )
    assert Mandat.objects.get(membre=a).date_fin is None
    assert not Mandat.objects.filter(membre=b).exists()


def test_installation_clot_aussi_un_mandat_ouvert_futur_de_la_meme_date(
    territoire, nouveau_membre, compte_technique
):
    t = territoire
    sec = Fonction.objects.get(nom="Secrétaire paroissial")
    a, b = nouveau_membre(t["P1"], "Adjovi"), nouveau_membre(t["P1"], "Bio")
    installer_bureau(
        unite=Unite("paroisse", t["P1"]),
        titulaires={sec: a},
        date_debut=datetime.date(2026, 3, 1),
        par=compte_technique,
    )
    installer_bureau(
        unite=Unite("paroisse", t["P1"]),
        titulaires={sec: b},
        date_debut=datetime.date(2026, 6, 1),
        par=compte_technique,
    )
    assert Mandat.objects.get(membre=a).date_fin == datetime.date(2026, 6, 1)
    assert Mandat.objects.filter(date_fin__isnull=True).count() == 1


# I3 — emails configurables, avec délai d'attente, et erreurs journalisées sans bloquer
def test_reglages_email_depuis_l_environnement():
    racine = Path(__file__).resolve().parents[3]
    env = {
        **os.environ,
        "DJANGO_DEBUG": "True",
        "DJANGO_EMAIL_HOST": "smtp.exemple.bj",
        "DJANGO_EMAIL_PORT": "587",
        "DJANGO_EMAIL_USE_TLS": "True",
    }
    code = (
        "from django.conf import settings as s;"
        "print(s.EMAIL_HOST, s.EMAIL_PORT, s.EMAIL_USE_TLS, s.EMAIL_TIMEOUT)"
    )
    r = subprocess.run(
        [sys.executable, "manage.py", "shell", "-c", code],
        cwd=racine,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "smtp.exemple.bj 587 True 10" in r.stdout, r.stderr


def test_echec_d_email_journalise_sans_bloquer(territoire, nouveau_membre, monkeypatch, caplog):
    from apps.notifications import services

    m = nouveau_membre(territoire["P1"], "Mail")
    m.email = "m@exemple.bj"
    m.save()

    def panne(*a, **k):
        raise OSError("serveur injoignable")

    monkeypatch.setattr(services, "send_mail", panne)
    assert services.notifier([m.compte], "Bonjour") == 1
    assert "serveur injoignable" in caplog.text


# I5 — les alertes d'échéance mènent à une page accessible au destinataire
def test_lien_d_alerte_accessible_aux_bureaux(monde):
    Mandat.objects.exclude(membre=monde["sec_p1"]).update(date_fin_prevue=datetime.date(2030, 1, 1))
    m = monde["sec_p1"].mandats.get()
    m.date_fin_prevue = datetime.date(2027, 1, 9)
    m.save()
    alertes_echeances(datetime.date(2026, 11, 10))
    n = Notification.objects.get(destinataire=monde["sec_p1"].compte)
    assert n.lien == "/"  # l'accueil, accessible à tous les destinataires


# I7 — un BNC sans fonction de gestion verrouillerait le site : refusé
def test_bnc_sans_fonction_de_gestion_refuse(territoire, nouveau_membre, compte_technique):
    m = nouveau_membre(territoire["P1"], "Tresorier")
    with pytest.raises(InstallationRefusee, match="Président ou Secrétaire national"):
        installer_bureau(
            unite=Unite("national", None),
            titulaires={Fonction.objects.get(nom="Trésorier national"): m},
            date_debut=datetime.date(2026, 11, 10),
            par=compte_technique,
        )
