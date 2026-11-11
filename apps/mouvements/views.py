from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite, membre_pour_mutation, unite_depuis_cle, unites_gerees
from apps.mouvements.forms import AvisForm, NouvelleMutationForm
from apps.mouvements.models import EtatDemande, Mutation, Signalement
from apps.mouvements.services import (
    MouvementRefuse,
    demander_mutation,
    donner_avis,
    mutations_pour_unite,
)


def _mutation_visible(unite: Unite, pk: int) -> Mutation:
    mutation = mutations_pour_unite(unite).filter(pk=pk).first()
    if mutation is None:
        raise Http404
    return mutation


def niveau_avis(unite: Unite, mutation: Mutation) -> str | None:
    """« circuit » ou « region » si cette unité est celle de départ et que son avis manque."""
    if mutation.etat != EtatDemande.AVIS:
        return None
    depart = mutation.paroisse_depart
    if unite.niveau == Niveau.CIRCUIT and unite.objet == depart.circuit:
        niveau = "circuit"
    elif unite.niveau == Niveau.REGION and unite.objet == depart.circuit.region:
        niveau = "region"
    else:
        return None
    return None if mutation.avis.filter(niveau=niveau).exists() else niveau


@login_required
def demandes(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    mutations = list(mutations_pour_unite(unite)[:200])
    mutations.sort(key=lambda m: not m.en_cours)
    signalements = Signalement.objects.filter(unite=cle).select_related("membre")[:200]
    return render(
        request,
        "mouvements/demandes.html",
        {"unite": unite, "mutations": mutations, "signalements": signalements},
    )


@login_required
def nouvelle_mutation(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    if unite.niveau not in (Niveau.PAROISSE, Niveau.NATIONAL):
        raise Http404
    national = unite.niveau == Niveau.NATIONAL
    form = NouvelleMutationForm(request.POST or None, national=national)
    apercu = None
    if request.method == "POST" and form.is_valid():
        membre = membre_pour_mutation(form.cleaned_data["matricule"])
        arrivee = form.cleaned_data["paroisse_arrivee"] if national else unite.objet
        if membre is None:
            form.add_error("matricule", "Aucun membre avec ce matricule.")
        elif request.POST.get("confirmer"):
            try:
                mutation = demander_mutation(
                    membre=membre,
                    paroisse_arrivee=arrivee,
                    par=request.user,
                    motif=form.cleaned_data["motif"],
                )
            except MouvementRefuse as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Demande de mutation enregistrée.")
                return redirect("mouvements:mutation", cle=cle, pk=mutation.pk)
        else:
            actuelle = membre.affectation_actuelle
            apercu = {
                "nom": membre.nom_complet,
                "paroisse": actuelle.paroisse.nom if actuelle else "—",
                "arrivee": arrivee,
            }
    return render(
        request,
        "mouvements/nouvelle_mutation.html",
        {"unite": unite, "form": form, "apercu": apercu},
    )


@login_required
def mutation(request, cle, pk):
    unite = unite_depuis_cle(request.user, cle)
    mut = _mutation_visible(unite, pk)
    niveau = niveau_avis(unite, mut)
    return render(
        request,
        "mouvements/mutation.html",
        {
            "unite": unite,
            "mutation": mut,
            "avis": mut.avis.select_related("par"),
            "form_avis": AvisForm() if niveau else None,
        },
    )


@login_required
@require_POST
def avis(request, cle, pk):
    unite = unite_depuis_cle(request.user, cle)
    mut = _mutation_visible(unite, pk)
    niveau = niveau_avis(unite, mut)
    if niveau is None and unite.niveau in (Niveau.CIRCUIT, Niveau.REGION):
        depart = mut.paroisse_depart
        if unite.objet in (depart.circuit, depart.circuit.region):
            messages.error(request, "L'avis a déjà été donné ou n'est plus attendu.")
            return redirect("mouvements:mutation", cle=cle, pk=pk)
    if niveau is None:
        raise Http404
    form = AvisForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choisissez un avis favorable ou défavorable.")
        return redirect("mouvements:mutation", cle=cle, pk=pk)
    try:
        donner_avis(
            mutation=mut,
            niveau=niveau,
            favorable=form.cleaned_data["favorable"],
            commentaire=form.cleaned_data["commentaire"],
            par=request.user,
        )
        messages.success(request, "Avis enregistré.")
    except MouvementRefuse as exc:
        messages.error(request, str(exc))
    return redirect("mouvements:mutation", cle=cle, pk=pk)


@login_required
def mutation_aiguillage(request, pk):
    """Lien commun des notifications : renvoie vers la page de la mutation pour ce compte."""
    get_object_or_404(Mutation, pk=pk)
    if request.user.has_perm("membres.gerer_membres"):
        return redirect(f"/bureau/bn/mutations/{pk}/")
    for unite in unites_gerees(request.user):
        if mutations_pour_unite(unite).filter(pk=pk).exists():
            return redirect(reverse("mouvements:mutation", args=[unite.cle, pk]))
    raise Http404
