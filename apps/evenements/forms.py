"""Formulaire d'un événement (décisions du mainteneur du 13/11/2026).

- Date (JJ/MM/AAAA) et heure dans deux champs séparés.
- Date passée : « Revérifiez votre date », sauf confirmation (événement déjà tenu).
- Sections : option à part ; les noms s'écrivent à la main, une par ligne.
"""

import datetime

from django import forms
from django.utils import timezone

_DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
_HEURE = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
FORMATS_DATE = ["%Y-%m-%d", "%d/%m/%Y"]


def _combiner(date: datetime.date | None, heure: datetime.time | None):
    if date is None:
        return None
    return timezone.make_aware(datetime.datetime.combine(date, heure or datetime.time(0, 0)))


class EvenementForm(forms.Form):
    nom = forms.CharField(label="Dénomination", max_length=200)
    debut_date = forms.DateField(label="Date", widget=_DATE, input_formats=FORMATS_DATE)
    debut_heure = forms.TimeField(label="Heure", widget=_HEURE)
    confirmer_date_passee = forms.BooleanField(
        label="Je confirme cette date passée (événement déjà tenu)", required=False
    )
    fin_date = forms.DateField(
        label="Date de fin (facultatif)", widget=_DATE, required=False, input_formats=FORMATS_DATE
    )
    fin_heure = forms.TimeField(label="Heure de fin", widget=_HEURE, required=False)
    lieu = forms.CharField(label="Lieu", max_length=200, required=False)
    description = forms.CharField(
        label="Description", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    avec_sections = forms.BooleanField(
        label="Organiser l'événement en sections",
        required=False,
        help_text="Seulement si l'événement en a besoin.",
    )
    sessions = forms.CharField(
        label="Sections (une par ligne)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Section Mer\nSection Culte"}),
        help_text="Écrivez vous-même les sections de cet événement, une par ligne.",
    )
    avec_autorisation = forms.BooleanField(
        label="Générer une autorisation pour les convoqués",
        required=False,
        help_text="Une carte avec photo et QR code, à imprimer ou à montrer sur le téléphone.",
    )
    validite_date = forms.DateField(
        label="Autorisation valable à partir du",
        widget=_DATE,
        required=False,
        input_formats=FORMATS_DATE,
        help_text="Vide : à partir du début de l'événement.",
    )
    validite_heure = forms.TimeField(label="À partir de l'heure", widget=_HEURE, required=False)
    validite_heures = forms.TypedChoiceField(
        label="Durée de validité de l'autorisation",
        coerce=int,
        required=False,
        empty_value=24,
        choices=[
            (6, "6 heures"),
            (12, "12 heures"),
            (24, "24 heures"),
            (48, "48 heures"),
            (72, "72 heures"),
            (96, "4 jours"),
            (168, "7 jours"),
        ],
        initial=24,
        help_text="Après ce délai, l'autorisation n'est plus valable au contrôle.",
    )

    def __init__(self, *args, deja_cree: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.deja_cree = deja_cree

    @staticmethod
    def initial_depuis(ev) -> dict:
        def separer(prefixe, valeur):
            if not valeur:
                return {}
            local = timezone.localtime(valeur)
            return {f"{prefixe}_date": local.date(), f"{prefixe}_heure": local.time()}

        return {
            "nom": ev.nom,
            **separer("debut", ev.debut),
            **separer("fin", ev.fin),
            **separer("validite", ev.validite_debut),
            "lieu": ev.lieu,
            "description": ev.description,
            "avec_sections": ev.avec_sections,
            "sessions": "\n".join(ev.sessions.values_list("nom", flat=True)),
            "avec_autorisation": ev.avec_autorisation,
            "validite_heures": ev.validite_heures,
        }

    def clean(self):
        d = super().clean()
        d["debut"] = _combiner(d.get("debut_date"), d.get("debut_heure"))
        d["fin"] = _combiner(d.get("fin_date"), d.get("fin_heure")) if d.get("fin_date") else None
        d["validite_debut"] = (
            _combiner(d.get("validite_date"), d.get("validite_heure"))
            if d.get("validite_date")
            else None
        )
        debut = d["debut"]
        if debut and debut < timezone.now() and not d.get("confirmer_date_passee"):
            if (
                not self.deja_cree
                or "debut_date" in self.changed_data
                or ("debut_heure" in self.changed_data)
            ):
                self.add_error(
                    "debut_date",
                    "Revérifiez votre date : elle est déjà passée. S'il s'agit d'un événement "
                    "déjà tenu, cochez « Je confirme cette date passée ».",
                )
        if d["fin"] and debut and d["fin"] < debut:
            self.add_error("fin_date", "La fin ne peut pas précéder le début.")
        return d

    def liste_sessions(self) -> list[str]:
        if not self.cleaned_data.get("avec_sections"):
            return []
        return [s.strip() for s in self.cleaned_data.get("sessions", "").splitlines() if s.strip()]
