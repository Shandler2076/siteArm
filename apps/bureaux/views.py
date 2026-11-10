from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render

from apps.bureaux.perimetre import (
    anciens_membres,
    membres_visibles,
    unite_depuis_cle,
    unites_gerees,
)


@login_required
def accueil(request):
    unites = unites_gerees(request.user)
    if not unites:
        raise PermissionDenied
    if len(unites) == 1:
        return redirect("bureaux:membres", cle=unites[0].cle)
    return render(request, "bureaux/choisir_unite.html", {"unites": unites})


@login_required
def membres(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    qs = membres_visibles(unite).order_by("nom", "prenoms")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(matricule__icontains=q) | Q(nom__icontains=q) | Q(prenoms__icontains=q))
    page = Paginator(qs.prefetch_related("affectations__paroisse"), 50).get_page(
        request.GET.get("page")
    )
    return render(request, "bureaux/membres.html", {"unite": unite, "page": page, "q": q})


@login_required
def fiche_membre(request, cle, matricule):
    unite = unite_depuis_cle(request.user, cle)
    membre = membres_visibles(unite).filter(matricule=matricule).first()
    if membre is None:
        raise Http404
    parcours = membre.affectations.select_related("paroisse", "circuit_a_date", "region_a_date")
    mandats = membre.mandats.select_related("fonction", "paroisse", "circuit", "region")
    return render(
        request,
        "bureaux/fiche_membre.html",
        {
            "unite": unite,
            "membre": membre,
            "parcours": parcours,
            "mandats": mandats,
        },
    )


@login_required
def anciens(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    lignes = []
    for a in anciens_membres(unite)[:500]:
        actuelle = a.membre.affectation_actuelle
        lignes.append({"affectation": a, "membre": a.membre, "actuelle": actuelle})
    return render(request, "bureaux/anciens.html", {"unite": unite, "lignes": lignes})
