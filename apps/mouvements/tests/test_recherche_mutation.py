"""Faille M3 : l'aperçu d'une mutation montre le nom et la paroisse d'un membre à partir de son
matricule ; chaque recherche est inscrite au journal et leur nombre est limité par jour."""

from html import unescape

from apps.journal.models import RECHERCHE_MATRICULE, EntreeJournal


def test_apercu_de_mutation_journalise_et_limite(client, monde, settings):
    settings.LIMITE_RECHERCHES_MATRICULE = 2
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/mutations/nouvelle/"
    for cible in (monde["m2"], monde["m3"]):
        r = client.post(url, {"matricule": cible.matricule})
        assert cible.nom_complet in unescape(r.content.decode())
    assert (
        EntreeJournal.objects.filter(
            action=RECHERCHE_MATRICULE, auteur=monde["sec_p1"].compte
        ).count()
        == 2
    )
    cible = monde["m4"]
    page = unescape(client.post(url, {"matricule": cible.matricule}).content.decode())
    assert cible.nom_complet not in page and "trop de recherches" in page.lower()


def test_confirmer_sans_apercu_est_compte(client, monde, settings):
    settings.LIMITE_RECHERCHES_MATRICULE = 1
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/mutations/nouvelle/"
    client.post(url, {"matricule": "2015-01AS-9999", "confirmer": "1"})
    page = unescape(
        client.post(url, {"matricule": monde["m3"].matricule, "confirmer": "1"}).content.decode()
    )
    assert "trop de recherches" in page.lower()


def test_la_derniere_recherche_peut_etre_confirmee(client, monde, settings):
    from apps.mouvements.models import Mutation

    settings.LIMITE_RECHERCHES_MATRICULE = 1
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/mutations/nouvelle/"
    cible = monde["m2"]
    client.post(url, {"matricule": cible.matricule})
    r = client.post(url, {"matricule": cible.matricule, "motif": "Déménagement", "confirmer": "1"})
    assert r.status_code == 302 and Mutation.objects.filter(membre=cible).exists()
