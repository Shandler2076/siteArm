from django import forms

_DT = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


class EvenementForm(forms.Form):
    nom = forms.CharField(label="Dénomination", max_length=200)
    debut = forms.DateTimeField(label="Date et heure", widget=_DT, input_formats=["%Y-%m-%dT%H:%M"])
    fin = forms.DateTimeField(
        label="Fin (facultatif)", widget=_DT, required=False, input_formats=["%Y-%m-%dT%H:%M"]
    )
    lieu = forms.CharField(label="Lieu", max_length=200, required=False)
    description = forms.CharField(
        label="Description", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    avec_autorisation = forms.BooleanField(
        label="Générer une autorisation (carte) pour les convoqués",
        required=False,
        help_text="Pour les grands événements où il faut être autorisé à travailler.",
    )
    sessions = forms.CharField(
        label="Sessions (une par ligne)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Par exemple : Session Mère, Session Culte, Session Fruits.",
    )

    def liste_sessions(self) -> list[str]:
        return [s.strip() for s in self.cleaned_data.get("sessions", "").splitlines() if s.strip()]
