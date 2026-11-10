from django import forms

MESSAGE_BORNES = (
    "Saisissez des âges croissants entre 1 et 120, séparés par des virgules (ex. : 18, 40)."
)


class BornesForm(forms.Form):
    bornes = forms.CharField(
        label="Bornes (âges séparés par des virgules)",
        max_length=60,
        error_messages={"required": MESSAGE_BORNES},
    )

    def clean_bornes(self) -> str:
        morceaux = [m.strip() for m in self.cleaned_data["bornes"].split(",")]
        if not 1 <= len(morceaux) <= 6 or not all(m.isascii() and m.isdigit() for m in morceaux):
            raise forms.ValidationError(MESSAGE_BORNES)
        ages = [int(m) for m in morceaux]
        if any(not 1 <= a <= 120 for a in ages) or ages != sorted(set(ages)):
            raise forms.ValidationError(MESSAGE_BORNES)
        return ",".join(str(a) for a in ages)
