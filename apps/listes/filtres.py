"""Formulaire de filtres des listes et requête correspondante (toujours dans le périmètre)."""

import datetime

from django import forms
from django.http import QueryDict
from django.utils import timezone

from apps.bureaux.models import Fonction, Mandat, Niveau
from apps.bureaux.perimetre import Unite, membres_visibles
from apps.listes.ages import filtrer_age
from apps.listes.colonnes import COLONNES_LISTE, COLONNES_PAR_DEFAUT
from apps.membres.models import Categorie, Membre, Sexe, Statut
from apps.organisation.models import Circuit, Paroisse, Region

AGES = [
    ("", "Tous les âges"),
    ("moins", "Moins de X ans"),
    ("plus", "Plus de X ans"),
    ("entre", "Entre X et Y ans (inclus)"),
    ("inconnu", "Âge non renseigné"),
]


class _ChoixUnite(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.nom if obj.active else f"{obj.nom} (fermée)"


class _ChoixFonction(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.nom} — {obj.get_niveau_display()}"


class FiltreListeForm(forms.Form):
    statut = forms.MultipleChoiceField(
        label="Statut", choices=Statut.choices, required=False, widget=forms.CheckboxSelectMultiple
    )
    sexe = forms.ChoiceField(label="Sexe", choices=[("", "Tous")] + Sexe.choices, required=False)
    categorie = forms.ChoiceField(
        label="Catégorie", choices=[("", "Toutes")] + Categorie.choices, required=False
    )
    annee = forms.IntegerField(label="Année d'intégration", required=False, min_value=1900)
    fonction = _ChoixFonction(
        label="Fonction (en cours)",
        queryset=Fonction.objects.order_by("niveau", "ordre"),
        required=False,
        empty_label="Toutes",
    )
    age = forms.ChoiceField(label="Âge", choices=AGES, required=False)
    age_x = forms.IntegerField(label="X (ans)", required=False, min_value=0, max_value=130)
    age_y = forms.IntegerField(label="Y (ans)", required=False, min_value=0, max_value=130)
    colonnes = forms.MultipleChoiceField(
        label="Colonnes",
        choices=[(k, v[0]) for k, v in COLONNES_LISTE.items()],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    envoye = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, unite: Unite, data: QueryDict | None = None):
        data = (data or QueryDict("")).copy()
        if not data.get("envoye"):
            if not data.getlist("statut"):
                data.setlist("statut", [Statut.ACTIF])
            data["envoye"] = "1"
        super().__init__(data)
        self.unite = unite
        objet = unite.objet
        nouveaux = {}
        if unite.niveau == Niveau.NATIONAL:
            nouveaux["region"] = _ChoixUnite(
                label="Région", queryset=Region.objects.order_by("code"), required=False
            )
        if unite.niveau in (Niveau.NATIONAL, Niveau.REGION):
            circuits = Circuit.objects.order_by("nom")
            if unite.niveau == Niveau.REGION:
                circuits = circuits.filter(region=objet)
            nouveaux["circuit"] = _ChoixUnite(label="Circuit", queryset=circuits, required=False)
        if unite.niveau != Niveau.PAROISSE:
            paroisses = Paroisse.objects.order_by("nom")
            if unite.niveau == Niveau.REGION:
                paroisses = paroisses.filter(circuit__region=objet)
            elif unite.niveau == Niveau.CIRCUIT:
                paroisses = paroisses.filter(circuit=objet)
            nouveaux["paroisse"] = _ChoixUnite(label="Paroisse", queryset=paroisses, required=False)
        if unite.niveau == Niveau.NATIONAL:
            nouveaux["sans_affectation"] = forms.BooleanField(
                label="Sans affectation actuelle", required=False
            )
        for nom, champ in nouveaux.items():
            champ.empty_label = "Toutes"
            self.fields[nom] = champ
        ordre = ["statut", "sexe", "categorie", "region", "circuit", "paroisse", "annee"]
        self.order_fields(ordre)

    def clean_annee(self):
        annee = self.cleaned_data.get("annee")
        if annee is not None and annee > timezone.localdate().year:
            raise forms.ValidationError("Année d'intégration dans le futur.")
        return annee

    def clean_colonnes(self):
        return self.cleaned_data.get("colonnes") or list(COLONNES_PAR_DEFAUT)

    def clean(self):
        donnees = super().clean()
        age, x, y = donnees.get("age"), donnees.get("age_x"), donnees.get("age_y")
        if age in ("moins", "plus", "entre") and x is None and "age_x" not in self.errors:
            self.add_error("age_x", "Indiquez l'âge X.")
        if age == "entre":
            if y is None and "age_y" not in self.errors:
                self.add_error("age_y", "Indiquez l'âge Y.")
            elif x is not None and y is not None and y < x:
                self.add_error(
                    "age_y", "L'âge maximum doit être supérieur ou égal à l'âge minimum."
                )
        return donnees


def membres_filtres(unite: Unite, donnees: dict, aujourdhui: datetime.date):
    qs = Membre.objects.filter(pk__in=membres_visibles(unite).values("pk"))
    if donnees.get("statut"):
        qs = qs.filter(statut__in=donnees["statut"])
    for champ in ("sexe", "categorie"):
        if donnees.get(champ):
            qs = qs.filter(**{champ: donnees[champ]})
    if donnees.get("annee"):
        qs = qs.filter(annee_integration=donnees["annee"])
    lieux = {
        "paroisse": "affectations__paroisse",
        "circuit": "affectations__paroisse__circuit",
        "region": "affectations__paroisse__circuit__region",
    }
    for champ, chemin in lieux.items():
        if donnees.get(champ):
            qs = qs.filter(**{"affectations__date_fin__isnull": True, chemin: donnees[champ]})
    if donnees.get("sans_affectation"):
        qs = qs.exclude(affectations__date_fin__isnull=True)
    if donnees.get("fonction"):
        en_cours = Mandat.objects.en_cours(aujourdhui).filter(fonction=donnees["fonction"])
        qs = qs.filter(pk__in=en_cours.values("membre"))
    if donnees.get("age"):
        qs = filtrer_age(qs, donnees["age"], donnees.get("age_x"), donnees.get("age_y"), aujourdhui)
    return qs.order_by("nom", "prenoms", "matricule")


def resume_filtres(form: FiltreListeForm) -> list[str]:
    d = form.cleaned_data
    resume = []
    if d.get("statut"):
        libelles = dict(Statut.choices)
        resume.append("Statut : " + ", ".join(str(libelles[s]) for s in d["statut"]))
    if d.get("sexe"):
        resume.append(f"Sexe : {Sexe(d['sexe']).label}")
    if d.get("categorie"):
        resume.append(f"Catégorie : {Categorie(d['categorie']).label}")
    for champ, libelle in (("region", "Région"), ("circuit", "Circuit"), ("paroisse", "Paroisse")):
        if d.get(champ):
            resume.append(f"{libelle} : {d[champ].nom}")
    if d.get("sans_affectation"):
        resume.append("Sans affectation actuelle")
    if d.get("annee"):
        resume.append(f"Année d'intégration : {d['annee']}")
    if d.get("fonction"):
        resume.append(f"Fonction : {d['fonction'].nom}")
    age, x, y = d.get("age"), d.get("age_x"), d.get("age_y")
    if age == "moins":
        resume.append(f"Âge : moins de {x} ans")
    elif age == "plus":
        resume.append(f"Âge : plus de {x} ans")
    elif age == "entre":
        resume.append(f"Âge : entre {x} et {y} ans")
    elif age == "inconnu":
        resume.append("Âge : non renseigné")
    return resume or ["Aucun filtre"]
