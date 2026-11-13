"""Filtres d'affichage des cotisations."""

from django import template

register = template.Library()

_COURTS = {
    "janvier": "Janv", "février": "Févr", "mars": "Mars", "avril": "Avr",
    "mai": "Mai", "juin": "Juin", "juillet": "Juil", "août": "Août",
    "septembre": "Sept", "octobre": "Oct", "novembre": "Nov", "décembre": "Déc",
}  # fmt: skip


@register.filter
def mois_court(nom: str) -> str:
    """Abréviation sans ambiguïté (juin ≠ juillet)."""
    return _COURTS.get(str(nom).lower(), str(nom)[:3].capitalize())
