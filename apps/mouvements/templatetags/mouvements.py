from django import template

from apps.membres.models import Statut
from apps.mouvements.models import TypeHistorique

register = template.Library()


@register.filter
def date_deces(membre):
    """Date d'effet du décès inscrite dans l'historique (ou None)."""
    if membre.statut != Statut.DECEDE:
        return None
    h = (
        membre.historique.filter(type=TypeHistorique.STATUT, nouveau=Statut.DECEDE)
        .order_by("-date_effet", "-pk")
        .first()
    )
    return h.date_effet if h else None


@register.filter
def etat_sanction(sanction) -> str:
    from django.utils import timezone

    if sanction.levee_le:
        return f"Levée le {sanction.levee_le:%d/%m/%Y}"
    if sanction.en_cours(timezone.localdate()):
        return "En cours"
    if sanction.date_debut > timezone.localdate():
        return "À venir"
    return "Terminée"


@register.filter
def en_cours_ou_a_venir(sanction) -> bool:
    from django.utils import timezone

    jour = timezone.localdate()
    return sanction.levee_le is None and (sanction.date_fin is None or jour < sanction.date_fin)
