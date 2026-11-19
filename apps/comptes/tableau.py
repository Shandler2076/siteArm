"""Tuiles de « Ma page » (tableau de bord du style coloré, décision du 19/11/2026).

Chaque tuile ne montre que ce que le compte voit déjà ailleurs (mêmes règles que les pages
qu'elle ouvre) ; aucune donnée d'un autre membre."""

from django.urls import reverse
from django.utils import timezone


def _membre(compte):
    from apps.membres.models import Membre

    try:
        return compte.membre
    except Membre.DoesNotExist:
        return None


def _cotisations(membre) -> dict:
    from apps.cotisations.models import premier_du_mois
    from apps.cotisations.regles import situation

    s = situation(membre, premier_du_mois(timezone.localdate()))
    if s.a_jour:
        valeur, variante = "À jour", "vert"
    else:
        valeur = f"{s.retard} mois à régler"
        variante = "alerte"
    return {
        "libelle": "Mes cotisations",
        "valeur": valeur,
        "url": reverse("cotisations:moi"),
        "variante": variante,
        "texte": True,
    }


def _prochain_evenement(membre) -> dict | None:
    from apps.evenements.models import EtatEvenement

    c = (
        membre.convocations.filter(
            active=True,
            evenement__etat=EtatEvenement.PREVU,
            evenement__debut__gte=timezone.now(),
        )
        .select_related("evenement")
        .order_by("evenement__debut")
        .first()
    )
    if c is None:
        return None
    ev = c.evenement
    return {
        "libelle": "Prochain événement",
        "valeur": f"{ev.nom} · {timezone.localtime(ev.debut):%d/%m}",
        "url": reverse("evenements:moi"),
        "variante": "or",
        "texte": True,
    }


def tuiles(compte) -> list[dict]:
    from apps.bureaux.menu import _nb_a_signer, _nb_decisions

    resultat = []
    a_signer = _nb_a_signer(compte)
    if a_signer:
        resultat.append(
            {
                "libelle": "Courriers à signer",
                "valeur": a_signer,
                "url": reverse("courrier:a_signer"),
                "variante": "bordeaux",
            }
        )
    if compte.has_perm("membres.gerer_membres"):
        resultat.append(
            {
                "libelle": "Décisions à prendre",
                "valeur": _nb_decisions(),
                "url": reverse("mouvements:bn_decisions"),
                "variante": "marine",
            }
        )
    membre = _membre(compte)
    if membre is not None:
        resultat.append(_cotisations(membre))
        evenement = _prochain_evenement(membre)
        if evenement:
            resultat.append(evenement)
    non_lues = compte.notifications.filter(lue=False).count()
    resultat.append(
        {
            "libelle": "Notifications non lues",
            "valeur": non_lues,
            "url": reverse("notifications:liste"),
            "variante": "blanc",
        }
    )
    return resultat
