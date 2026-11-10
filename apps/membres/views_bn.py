from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.membres.forms import FormulaireEnregistrement
from apps.membres.models import Membre
from apps.membres.pdf import fiche_identification_pdf
from apps.membres.services import (
    CapaciteMatriculeAtteinte,
    doublons_possibles,
    enregistrer_membre,
    generer_mot_de_passe_provisoire,
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


def _reponse_pdf(contenu: bytes, matricule: str) -> HttpResponse:
    r = HttpResponse(contenu, content_type="application/pdf")
    r["Content-Disposition"] = f'attachment; filename="fiche-{matricule}.pdf"'
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
@gerer_membres
@require_POST
def fiche_identifiants_pdf(request, matricule):
    """Nouveau mot de passe provisoire et fiche avec identifiants (mot de passe jamais stocké)."""
    membre = get_object_or_404(Membre, matricule=matricule)
    mot_de_passe = generer_mot_de_passe_provisoire()
    compte = membre.compte
    compte.set_password(mot_de_passe)
    compte.doit_changer_mot_de_passe = True
    compte.save(update_fields=["password", "doit_changer_mot_de_passe"])
    return _reponse_pdf(fiche_identification_pdf(membre, mot_de_passe), matricule)


@login_required
@gerer_membres
def fiche_pdf(request, matricule):
    membre = get_object_or_404(Membre, matricule=matricule)
    return _reponse_pdf(fiche_identification_pdf(membre), matricule)
