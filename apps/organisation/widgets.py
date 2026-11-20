"""Liste déroulante avec recherche (demande du 20/11/2026).

Le script du site (`static/js/site.js::listeAvecRecherche`) place au-dessus une zone de saisie :
on tape quelques lettres (sans souci des accents) et seules les entrées correspondantes
s'affichent. Sans script, la liste reste une liste déroulante ordinaire.
"""

from django import forms


class ListeAvecRecherche(forms.Select):
    def __init__(self, attrs=None, choices=()):
        attrs = {"data-recherche": "", **(attrs or {})}
        super().__init__(attrs, choices)
