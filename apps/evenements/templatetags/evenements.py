from django import template

from apps.evenements.services import autorisation_valable

register = template.Library()


@register.simple_tag
def convocations_de(membre):
    """Historique des événements d'un membre (convocations, actives ou retirées)."""
    return membre.convocations.select_related("evenement", "session").order_by("-evenement__debut")


@register.simple_tag
def autorisations_valables(membre):
    return [
        c
        for c in membre.convocations.filter(active=True).select_related("evenement", "session")
        if autorisation_valable(c)
    ]
