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
