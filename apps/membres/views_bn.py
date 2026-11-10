from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.membres.forms import FormulaireEnregistrement
from apps.membres.models import Membre
from apps.membres.services import (
    CapaciteMatriculeAtteinte,
    doublons_possibles,
    enregistrer_membre,
)

gerer_membres = permission_required("membres.gerer_membres", raise_exception=True)


@login_required
@gerer_membres
def enregistrer(request):
    form = FormulaireEnregistrement(request.POST or None, request.FILES or None)
    doublons = []
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        doublons = list(
            doublons_possibles(
                nom=cd["nom"], prenoms=cd["prenoms"], date_naissance=cd.get("date_naissance"),
                npi=cd.get("npi", ""),
            ).select_related("paroisse_integration")
        )
        if doublons and not cd.get("confirmer_malgre_doublon"):
            form.data = form.data.copy()
            form.data["confirmer_malgre_doublon"] = "on"
        else:
            try:
                res = enregistrer_membre(
                    donnees=form.donnees_membre(),
                    paroisse_integration=cd["paroisse_integration"],
                    annee_integration=cd["annee_integration"],
                    par=request.user,
                )
            except CapaciteMatriculeAtteinte as e:
                form.add_error(None, str(e))
                doublons = []
            else:
                messages.success(request, f"Membre enregistré : matricule {res.membre.matricule}")
                return redirect("membres:bn_fiche", matricule=res.membre.matricule)
    return render(request, "membres/bn_enregistrer.html", {"form": form, "doublons": doublons})


@login_required
@gerer_membres
def fiche(request, matricule):
    membre = get_object_or_404(
        Membre.objects.select_related("paroisse_integration", "region_integration"),
        matricule=matricule,
    )
    return render(request, "membres/bn_fiche.html", {"membre": membre})
