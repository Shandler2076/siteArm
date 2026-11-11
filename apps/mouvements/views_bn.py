from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.bureaux.views_bn import bn_requis
from apps.mouvements.models import EN_COURS, EtatDemande, Mutation, Signalement
from apps.mouvements.services import (
    MouvementRefuse,
    decider_mutation,
    decider_signalement,
    mandats_a_clore,
)


@bn_requis
def decisions(request):
    mutations = (
        Mutation.objects.filter(etat__in=EN_COURS)
        .select_related("membre", "paroisse_depart", "paroisse_arrivee")
        .order_by("date_demande", "pk")
    )
    signalements = (
        Signalement.objects.filter(etat=EtatDemande.BN)
        .select_related("membre")
        .order_by("date_demande", "pk")
    )
    return render(
        request,
        "mouvements/bn_decisions.html",
        {"mutations": mutations, "signalements": signalements},
    )


@bn_requis
def mutation(request, pk):
    mut = get_object_or_404(
        Mutation.objects.select_related("membre", "paroisse_depart", "paroisse_arrivee"), pk=pk
    )
    erreur = None
    if request.method == "POST":
        decision = request.POST.get("decision")
        if decision in ("valider", "refuser"):
            try:
                decider_mutation(
                    mutation=mut,
                    valider=decision == "valider",
                    par=request.user,
                    commentaire=request.POST.get("commentaire", "")[:300],
                )
            except MouvementRefuse as exc:
                erreur = str(exc)
            else:
                messages.success(
                    request, "Mutation validée." if decision == "valider" else "Mutation refusée."
                )
                return redirect("mouvements:bn_mutation", pk=pk)
        mut.refresh_from_db()
    avis = {a.niveau: a for a in mut.avis.all()}
    return render(
        request,
        "mouvements/bn_mutation.html",
        {
            "mutation": mut,
            "avis": list(avis.values()),
            "avis_circuit": avis.get("circuit"),
            "avis_region": avis.get("region"),
            "mandats": mandats_a_clore(mut) if mut.en_cours else [],
            "erreur": erreur,
        },
    )


@bn_requis
def signalement(request, pk):
    sig = get_object_or_404(Signalement.objects.select_related("membre"), pk=pk)
    erreur = None
    if request.method == "POST":
        decision = request.POST.get("decision")
        motif = request.POST.get("motif_refus", "").strip()[:300]
        if decision == "refuser" and not motif:
            erreur = "Indiquez le motif du refus."
        elif decision in ("valider", "refuser"):
            try:
                resultat = decider_signalement(
                    signalement=sig,
                    confirmer=decision == "valider",
                    par=request.user,
                    motif_refus=motif,
                )
            except MouvementRefuse as exc:
                erreur = str(exc)
            else:
                if resultat.pdf:
                    r = HttpResponse(resultat.pdf, content_type="application/pdf")
                    nom = f"fiche-{sig.membre.matricule}.pdf"
                    r["Content-Disposition"] = f'attachment; filename="{nom}"'
                    r["Cache-Control"] = "private, no-store"
                    return r
                messages.success(
                    request,
                    "Signalement confirmé." if decision == "valider" else "Signalement refusé.",
                )
                return redirect("mouvements:bn_signalement", pk=pk)
        sig.refresh_from_db()
    return render(request, "mouvements/bn_signalement.html", {"signalement": sig, "erreur": erreur})
