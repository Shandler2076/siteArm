import datetime

from apps.notifications.models import Notification


def _post(client, membre_acteur, cle, cible):
    client.force_login(membre_acteur.compte)
    return client.post(f"/bureau/{cle}/membres/{cible.matricule}/reinitialiser/")


def test_paroisse_reinitialise_son_membre(client, monde, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        r = _post(client, monde["sec_p1"], f"paroisse-{monde['P1'].pk}", monde["m1"])
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    monde["m1"].compte.refresh_from_db()
    assert monde["m1"].compte.doit_changer_mot_de_passe
    assert Notification.objects.filter(
        destinataire=monde["m1"].compte, message__contains="réinitialisé"
    ).exists()


def test_bouton_visible_seulement_pour_la_paroisse(client, monde):
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/membres/{monde['m1'].matricule}/"
    assert "reinitialiser" in client.get(url).content.decode()
    client.force_login(monde["chef"].compte)
    url = f"/bureau/circuit-{monde['Ekpe A'].pk}/membres/{monde['m1'].matricule}/"
    assert "reinitialiser" not in client.get(url).content.decode()


def test_circuit_ne_reinitialise_pas(client, monde):
    r = _post(client, monde["chef"], f"circuit-{monde['Ekpe A'].pk}", monde["m1"])
    assert r.status_code == 403


def test_hors_perimetre_404(client, monde):
    r = _post(client, monde["sec_p1"], f"paroisse-{monde['P1'].pk}", monde["m3"])
    assert r.status_code == 404


def test_refus_sur_un_titulaire_de_mandat(client, monde, donner_mandat):
    cible = monde["m1"]
    donner_mandat(
        cible, "Coordinateur régional", monde["HOULENOU"], debut=datetime.date(2025, 1, 1)
    )
    ancien_hash = cible.compte.password
    r = _post(client, monde["sec_p1"], f"paroisse-{monde['P1'].pk}", cible)
    cible.compte.refresh_from_db()
    assert r.status_code == 403 and cible.compte.password == ancien_hash


def test_get_interdit(client, monde):
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/membres/{monde['m1'].matricule}/reinitialiser/"
    assert client.get(url).status_code == 405


def test_bn_reinitialise_un_secretaire_de_paroisse(client_technique, monde):
    r = client_technique.post(f"/membres/bn/{monde['sec_p1'].matricule}/fiche-identifiants.pdf")
    assert r.status_code == 200
