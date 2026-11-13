"""Pages de la trésorerie : droits, parcours de paiement simulé, confidentialité."""

from html import unescape

import pytest
from django.test import Client

from apps.cotisations.models import Versement
from apps.tresorerie import services as s
from apps.tresorerie.models import Contribution, Paiement


def _c(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _h(r):
    return unescape(r.content.decode())


def test_membre_paie_ses_mois_jusqu_au_recu(tresoriers, ouvert):
    m1 = tresoriers["m1"]
    c = _c(m1)
    assert "Payer par mobile money" in _h(c.get("/cotisations/moi/"))
    r = c.post("/tresorerie/payer/", {"nombre": "1"})
    p = Paiement.objects.get()
    assert r.status_code == 302 and r.url == f"/tresorerie/paiement/{p.reference}/"
    assert "simulée" in _h(c.get(r.url))
    c.post(r.url, {"action": "confirmer"})
    assert Versement.objects.filter(membre=m1, mode="mobile_money").count() == 1
    # Un autre membre ne voit pas ce paiement.
    assert _c(tresoriers["m2"]).get(r.url).status_code == 404


def test_payer_pour_un_autre_confirmation_reduite(tresoriers, ouvert):
    m1, m2 = tresoriers["m1"], tresoriers["m2"]
    html = _h(_c(m2).get("/tresorerie/payer-pour/", {"matricule": m1.matricule}))
    assert "Test A." in html  # prénom + initiale du nom
    assert m1.nom_complet not in html and m1.telephone not in html
    r = _c(m2).post(
        "/tresorerie/payer-pour/", {"matricule": m1.matricule, "confirmer": "1", "nombre": "1"}
    )
    assert r.status_code == 302 and Paiement.objects.get().objet["lignes"][0]["membre"] == m1.pk


def test_espace_tresorerie_droits(tresoriers):
    p1 = f"/tresorerie/paroisse-{tresoriers['P1'].pk}/"
    html = _h(_c(tresoriers["tresorier"]).get(p1))
    assert "Payer pour des membres" in html
    html = _h(_c(tresoriers["sec_p1"]).get(p1))
    assert "lecture seule" in html and "Payer pour des membres" not in html
    assert _c(tresoriers["m1"]).get(p1).status_code == 404
    assert _c(tresoriers["sec_p1"]).get(f"{p1}payer-membres/").status_code == 403


def test_tresorier_paie_pour_plusieurs_membres(tresoriers, ouvert):
    t = tresoriers
    c = _c(t["tresorier"])
    url = f"/tresorerie/paroisse-{t['P1'].pk}/payer-membres/"
    r = c.post(url, {f"n{t['m1'].pk}": "1", f"n{t['sec_p1'].pk}": "2"})
    p = Paiement.objects.get()
    assert r.status_code == 302 and p.montant == 300
    c.post(f"/tresorerie/paiement/{p.reference}/", {"action": "confirmer"})
    assert Versement.objects.filter(mode="mobile_money").count() == 2


def test_bn_cree_une_cotisation_et_bureau_paie_en_son_nom(tresoriers, client_technique):
    r = client_technique.post(
        "/tresorerie/bn/speciales/",
        {
            "libelle": "Contribution des paroisses",
            "type_montant": "fixe",
            "montant_fixe": "5000",
            "bureaux": ["paroisse"],
        },
    )
    assert r.status_code == 302
    cs = s.CotisationSpeciale.objects.get()
    c = _c(tresoriers["tresorier"])
    cle = f"paroisse-{tresoriers['P1'].pk}"
    assert "Payer au nom de" in _h(c.get(f"/tresorerie/{cle}/"))
    r = c.post(
        f"/tresorerie/speciale/{cs.pk}/payer/", {"bureau": cle, "type": "bureau", "montant": "5000"}
    )
    p = Paiement.objects.get()
    c.post(f"/tresorerie/paiement/{p.reference}/", {"action": "confirmer"})
    q = Contribution.objects.get()
    assert q.unite_cle == cle
    assert c.get(f"/tresorerie/quittance/{q.pk}.pdf").status_code == 200
    # Le secrétaire d'une autre paroisse ne peut pas payer au nom de P1.
    autre = _c(tresoriers["sec_p1"])
    r = autre.post(f"/tresorerie/speciale/{cs.pk}/payer/", {"bureau": cle, "montant": "1"})
    assert r.status_code == 403
    assert _c(tresoriers["m4"]).get(f"/tresorerie/quittance/{q.pk}.pdf").status_code == 404


@pytest.mark.parametrize("qui", ["m1", "tresorier", "sec_p1"])
def test_pages_bn_reservees(tresoriers, qui):
    c = _c(tresoriers[qui])
    for url in (
        "/tresorerie/bn/speciales/",
        "/tresorerie/bn/numeros/",
        "/tresorerie/bn/reversements/",
    ):
        assert c.get(url).status_code == 403, url


def test_reversements_roles(tresoriers, ouvert):
    import datetime

    from django.utils import timezone

    t = tresoriers
    s.confirmer_paiement(s.initier_paiement_mensuel(t["m1"].compte, [(t["m1"], 1)]))
    mois_dernier = (timezone.localdate().replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    Versement.objects.update(date_versement=mois_dernier + datetime.timedelta(days=3))
    url = f"/tresorerie/bn/reversements/?mois={mois_dernier:%Y-%m}"
    html = _h(_c(t["tresorier_national"]).get(url))
    assert "Aperçu des parts dues" in html and "Préparer l'état des reversements" in html
    assert "En attente de préparation par le Trésorier national" in html
    _c(t["tresorier_national"]).post(url, {"action": "preparer", "mois": f"{mois_dernier:%Y-%m}"})
    html = _h(_c(t["president"]).get(url))
    assert "Valider l'état préparé" in html and "Préparer l'état" not in html
    assert "En attente de validation" in html
    html = _h(_c(t["president"]).get("/tresorerie/bn/reversements/?mois=2020-01"))
    assert "Rien à reverser pour ce mois" in html


def test_payer_pour_ne_revele_pas_les_cotisations_ciblees(tresoriers, compte_technique):
    m1, m2 = tresoriers["m1"], tresoriers["m2"]
    s.creer_cotisation_speciale(
        libelle="Réservée aux Capitaines",
        type_montant="fixe",
        montant=1000,
        pour_membres="certains",
        criteres={"region": str(tresoriers["HOULENOU"].pk)},
        par=compte_technique,
    )
    s.creer_cotisation_speciale(
        libelle="Pour tous", type_montant="fixe", montant=500, par=compte_technique
    )
    html = _h(_c(m2).get("/tresorerie/payer-pour/", {"matricule": m1.matricule}))
    assert "Pour tous" in html and "Réservée aux Capitaines" not in html and "reste" not in html


def test_formulaire_bn_montant_devant_son_type_et_cibles(tresoriers, client_technique):
    html = _h(client_technique.get("/tresorerie/bn/speciales/"))
    for nom in ("montant_fixe", "montant_minimum", "montant_suggere", "unites", "bureaux"):
        assert f'name="{nom}"' in html
    assert "Membres désignés" in html and "Unités paroissiales" in html
    client_technique.post(
        "/tresorerie/bn/speciales/",
        {
            "libelle": "Pour une personne",
            "type_montant": "libre",
            "montant_suggere": "1000",
            "certains": "1",
            "membres": [str(tresoriers["m4"].pk)],
        },
    )
    cs = s.CotisationSpeciale.objects.get(libelle="Pour une personne")
    assert cs.membres_designes == [tresoriers["m4"].pk] and cs.montant_suggere == 1000
    assert s.concerne_membre(cs, tresoriers["m4"]) and not s.concerne_membre(cs, tresoriers["m1"])
