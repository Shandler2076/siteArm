import datetime

from apps.bureaux.models import Mandat
from apps.bureaux.services import alertes_echeances
from apps.notifications.models import Notification


def _seul_mandat_a_suivre(monde):
    """Les autres mandats du monde de test finissent loin : seul celui du secrétaire compte."""
    Mandat.objects.exclude(membre=monde["sec_p1"]).update(date_fin_prevue=datetime.date(2030, 1, 1))


def test_alerte_60_jours_une_seule_fois(monde, django_capture_on_commit_callbacks):
    _seul_mandat_a_suivre(monde)
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin_prevue = datetime.date(2027, 1, 9)
    mandat.save()
    with django_capture_on_commit_callbacks(execute=True):
        assert alertes_echeances(datetime.date(2026, 11, 9)) == (0, 0)
        assert alertes_echeances(datetime.date(2026, 11, 10)) == (1, 0)
        assert alertes_echeances(datetime.date(2026, 11, 11)) == (0, 0)
    n = Notification.objects.get(destinataire=monde["sec_p1"].compte)
    assert "arrive à échéance le 09/01/2027" in n.message and "Secrétaire paroissial" in n.message


def test_les_gestionnaires_nationaux_sont_prevenus(monde, donner_mandat):
    pres = monde["m4"]
    donner_mandat(pres, "Président", None, debut=datetime.date(2025, 1, 1))
    _seul_mandat_a_suivre(monde)
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin_prevue = datetime.date(2027, 1, 9)
    mandat.save()
    alertes_echeances(datetime.date(2026, 11, 10))
    assert Notification.objects.filter(
        destinataire=pres.compte, message__contains="arrive à échéance"
    ).exists()


def test_mandat_echu_signale_mais_pas_coupe(monde):
    from apps.bureaux.perimetre import unites_gerees

    _seul_mandat_a_suivre(monde)
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin_prevue = datetime.date(2026, 11, 1)
    mandat.alerte_echeance_le = datetime.date(2026, 9, 2)
    mandat.save()
    assert alertes_echeances(datetime.date(2026, 11, 10)) == (0, 1)
    assert alertes_echeances(datetime.date(2026, 11, 11)) == (0, 0)
    mandat.refresh_from_db()
    assert mandat.date_fin is None
    assert unites_gerees(monde["sec_p1"].compte, datetime.date(2026, 11, 10))
    assert Notification.objects.filter(message__contains="n'a pas été renouvelé").exists()


def test_commande(monde, capsys):
    from django.core.management import call_command

    call_command("verifier_echeances_mandats")
    assert "Échéances" in capsys.readouterr().out


def test_page_echeances_bn(client_technique, monde):
    _seul_mandat_a_suivre(monde)
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin_prevue = datetime.date.today() + datetime.timedelta(days=30)
    mandat.save()
    html = client_technique.get("/bureau/bn/echeances/").content.decode()
    assert "Secrétaire paroissial" in html and monde["sec_p1"].matricule in html


def test_page_echeances_reservee(client, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get("/bureau/bn/echeances/").status_code == 403
