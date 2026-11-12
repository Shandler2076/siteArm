import datetime

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.evenements.models import Convocation, Presence
from apps.evenements.services import (
    EvenementRefuse,
    annuler_evenement,
    autorisation_valable,
    convocation_par_jeton,
    convoquer,
    creer_evenement,
    modifier_evenement,
    pointer,
    retirer,
)
from apps.journal.models import EntreeJournal
from apps.notifications.models import Notification

DEBUT = timezone.make_aware(datetime.datetime(2026, 12, 24, 8, 0))


@pytest.fixture
def nativite(db, compte_technique):
    return creer_evenement(
        nom="Pèlerinage de la Nativité 2026",
        debut=DEBUT,
        lieu="Porto-Novo",
        avec_autorisation=True,
        sessions=["Session Mère", "Session Culte", "Session Fruits", " "],
        par=compte_technique,
    )


def test_creer_avec_sessions(nativite):
    assert [s.nom for s in nativite.sessions.all()] == [
        "Session Mère",
        "Session Culte",
        "Session Fruits",
    ]


def test_convoquer_notifie_et_ne_double_pas(
    nativite, monde, compte_technique, django_capture_on_commit_callbacks
):
    culte = nativite.sessions.get(nom="Session Culte")
    with django_capture_on_commit_callbacks(execute=True):
        faites = convoquer(
            nativite, [monde["m1"], monde["m2"]], session=culte, par=compte_technique
        )
    assert len(faites) == 2
    assert Notification.objects.filter(destinataire=monde["m1"].compte).exists()
    texte = Notification.objects.filter(destinataire=monde["m1"].compte).first().message
    assert "Bureau national" in texte and "Pèlerinage de la Nativité 2026" in texte
    assert "Session Culte" in texte
    convoquer(nativite, [monde["m1"]], session=culte, par=compte_technique)
    assert Convocation.objects.filter(evenement=nativite, membre=monde["m1"]).count() == 1
    mere = nativite.sessions.get(nom="Session Mère")
    convoquer(nativite, [monde["m1"]], session=mere, par=compte_technique)
    assert Convocation.objects.get(evenement=nativite, membre=monde["m1"]).session == mere


def test_reconvoquer_apres_retrait(nativite, monde, compte_technique):
    (c,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    retirer(c, motif="Indisponible", par=compte_technique)
    (c2,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    assert c2.pk != c.pk and c2.active
    assert Convocation.objects.filter(evenement=nativite, membre=monde["m1"]).count() == 2


def test_retrait_invalide_l_autorisation(nativite, monde, compte_technique):
    (c,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    assert autorisation_valable(c)
    with pytest.raises(EvenementRefuse, match="motif"):
        retirer(c, motif=" ", par=compte_technique)
    retirer(c, motif="Erreur", par=compte_technique)
    c.refresh_from_db()
    assert not autorisation_valable(c)


def test_annulation_notifie_et_invalide(
    nativite, monde, compte_technique, django_capture_on_commit_callbacks
):
    (c,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    with django_capture_on_commit_callbacks(execute=True):
        annuler_evenement(nativite, motif="Intempéries", par=compte_technique)
    c.refresh_from_db()
    assert not autorisation_valable(c)
    assert Notification.objects.filter(
        destinataire=monde["m1"].compte, message__contains="annulé"
    ).exists()


def test_report_notifie(nativite, monde, compte_technique, django_capture_on_commit_callbacks):
    convoquer(nativite, [monde["m1"]], par=compte_technique)
    with django_capture_on_commit_callbacks(execute=True):
        modifier_evenement(nativite, debut=DEBUT + datetime.timedelta(days=1), par=compte_technique)
    assert Notification.objects.filter(
        destinataire=monde["m1"].compte, message__contains="25/12/2026"
    ).exists()


def test_pointer_presence_et_refus_si_retire(nativite, monde, compte_technique):
    (c,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    pointer(c, Presence.PRESENT, par=compte_technique)
    c.refresh_from_db()
    assert c.presence == Presence.PRESENT and c.pointe_par == compte_technique
    retirer(c, motif="Erreur", par=compte_technique)
    with pytest.raises(EvenementRefuse):
        pointer(c, Presence.ABSENT, par=compte_technique)


def test_jeton_aleatoire_unique(nativite, monde, compte_technique):
    c1, c2 = convoquer(nativite, [monde["m1"], monde["m2"]], par=compte_technique)
    assert len(c1.jeton) >= 32 and c1.jeton != c2.jeton
    assert monde["m1"].matricule not in c1.jeton
    assert convocation_par_jeton(c1.jeton) == c1
    assert convocation_par_jeton("inventé") is None and convocation_par_jeton("") is None


def test_convocation_ne_se_supprime_pas(nativite, monde, compte_technique):
    (c,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    with pytest.raises(PermissionDenied):
        c.delete()


def test_journal_phrases_evenements(nativite, monde, compte_technique):
    from apps.journal.lecture import lire

    (c,) = convoquer(nativite, [monde["m1"]], par=compte_technique)
    pointer(c, Presence.PRESENT, par=compte_technique)
    textes = [ligne.texte for ligne in lire(EntreeJournal.objects.order_by("date"))]
    assert any(
        t.startswith("A créé l'événement « Pèlerinage de la Nativité 2026 »") for t in textes
    )
    assert any("A convoqué" in t and "Test ADJOVI" in t for t in textes)
    assert any("présent" in t and "Test ADJOVI" in t for t in textes)
