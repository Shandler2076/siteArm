from django import forms
from django.utils import timezone

from apps.membres.grades import Grade

_DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class PromotionForm(forms.Form):
    grade = forms.TypedChoiceField(label="Nouveau grade", coerce=int)
    date_effet = forms.DateField(label="Date d'effet", widget=_DATE)
    reference = forms.CharField(label="Référence de la décision du BNC", max_length=200)
    exceptionnelle = forms.BooleanField(
        label="Promotion exceptionnelle (art. 84)",
        required=False,
        help_text="Sans la durée minimale de l'art. 78, ou en sautant un grade.",
    )
    motif = forms.CharField(
        label="Motif (promotion exceptionnelle)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, grade_actuel: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        plancher = -1 if grade_actuel is None else grade_actuel
        self.fields["grade"].choices = [(v, lib) for v, lib in Grade.choices if v > plancher]
        self.fields["date_effet"].initial = timezone.localdate()


class SerieForm(forms.Form):
    grade = forms.TypedChoiceField(
        label="Grade à attribuer",
        coerce=int,
        choices=[(v, lib) for v, lib in Grade.choices if v > Grade.CAMARADE],
    )
    date_effet = forms.DateField(label="Date d'effet", widget=_DATE)
    reference = forms.CharField(label="Référence de la décision du BNC", max_length=200)


class CorrectionGradeForm(forms.Form):
    grade = forms.TypedChoiceField(label="Grade exact", coerce=int, choices=Grade.choices)
    date_effet = forms.DateField(label="Date de ce grade", widget=_DATE)
    motif = forms.CharField(
        label="Motif de la correction", widget=forms.Textarea(attrs={"rows": 2})
    )
