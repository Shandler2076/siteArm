"""Faille M3 : l'aperçu d'une mutation montre le nom et la paroisse d'un membre à partir de son
matricule ; chaque recherche est inscrite au journal et leur nombre est limité par jour."""

from html import unescape

from apps.journal.models import RECHERCHE_MATRICULE, EntreeJournal


def test_apercu_de_mutation_journalise_et_limite(client, monde, settings):
    settings.LIMITE_RECHERCHES_MATRICULE = 2
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/mutations/nouvelle/"
    cible = monde["m2"]
    for _ in range(2):
        r = client.post(url, {"matricule": cible.matricule})
        assert cible.nom_complet in unescape(r.content.decode())
    assert (
        EntreeJournal.objects.filter(
            action=RECHERCHE_MATRICULE, auteur=monde["sec_p1"].compte
        ).count()
        == 2
    )
    page = unescape(client.post(url, {"matricule": cible.matricule}).content.decode())
    assert cible.nom_complet not in page and "trop de recherches" in page.lower()
