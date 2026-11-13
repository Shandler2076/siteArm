"""Paroisse actuelle saisie à l'inscription sur le site (décision du 13/11/2026)."""

import datetime

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


def test_enregistrer_avec_paroisse_actuelle(territoire, compte_bn):
    t = territoire
    m = enregistrer_membre(
        donnees=dict(DONNEES),
        paroisse_integration=t["P1"],
        paroisse_actuelle=t["P4"],
        annee_integration=2015,
        par=compte_bn,
    ).membre
    jour = timezone.localdate()
    assert m.matricule.startswith("2015-03AS-")  # région d'intégration : le matricule ne bouge pas
    a1, a2 = m.affectations.order_by("date_debut", "pk")
    assert a1.paroisse == t["P1"] and a1.date_debut == datetime.date(2015, 1, 1)
    assert a1.date_fin == jour
    assert a2.paroisse == t["P4"] and a2.date_debut == jour and a2.date_fin is None
    assert a2.region_a_date == t["WEME"]
    assert a2.motif == "Paroisse actuelle à l'inscription sur le site"
    assert m.affectation_actuelle.paroisse == t["P4"]


def test_sans_paroisse_actuelle_inchange(territoire, compte_bn):
    t = territoire
    for actuelle in (None, t["P1"]):  # absente ou identique : une seule affectation
        m = enregistrer_membre(
            donnees=dict(DONNEES, nom=f"Test{bool(actuelle)}"),
            paroisse_integration=t["P1"],
            paroisse_actuelle=actuelle,
            annee_integration=2015,
            par=compte_bn,
        ).membre
        assert m.affectations.count() == 1


def test_paroisse_actuelle_gere_le_membre(territoire, compte_bn):
    from apps.bureaux.perimetre import Unite, membres_visibles

    t = territoire
    m = enregistrer_membre(
        donnees=dict(DONNEES),
        paroisse_integration=t["P1"],
        paroisse_actuelle=t["P4"],
        annee_integration=2015,
        par=compte_bn,
    ).membre
    assert m in membres_visibles(Unite("paroisse", t["P4"]))
    assert m not in membres_visibles(Unite("paroisse", t["P1"]))


def test_notification_a_la_paroisse_actuelle(
    territoire, compte_bn, donner_mandat, nouveau_membre, django_capture_on_commit_callbacks
):
    t = territoire
    sec_p4 = nouveau_membre(t["P4"], "SecP4")
    donner_mandat(sec_p4, "Secrétaire paroissial", t["P4"])
    sec_p1 = nouveau_membre(t["P1"], "SecP1")
    donner_mandat(sec_p1, "Secrétaire paroissial", t["P1"])
    with django_capture_on_commit_callbacks(execute=True):
        enregistrer_membre(
            donnees=dict(DONNEES),
            paroisse_integration=t["P1"],
            paroisse_actuelle=t["P4"],
            annee_integration=2015,
            par=compte_bn,
        )
    assert sec_p4.compte.notifications.filter(message__contains="HOUNKPÈ").exists()
    assert not sec_p1.compte.notifications.filter(message__contains="HOUNKPÈ").exists()


def test_formulaire_paroisse_actuelle(client_bn, territoire):
    t = territoire
    r = client_bn.get("/membres/bn/enregistrer/")
    assert 'name="paroisse_actuelle"' in r.content.decode()
    r = client_bn.post(
        "/membres/bn/enregistrer/",
        {
            **DONNEES,
            "annee_integration": "2015",
            "paroisse_integration": t["P1"].pk,
            "paroisse_actuelle": t["P3"].pk,
        },
    )
    assert r.status_code == 302
    m = Membre.objects.get(nom__iexact="Hounkpè")
    assert m.affectation_actuelle.paroisse == t["P3"]
