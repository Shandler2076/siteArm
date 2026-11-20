from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.bureaux.views_bn import bn_requis, permission_requise
from apps.mouvements.models import EN_COURS, EtatDemande, Mutation, Signalement
from apps.mouvements.services import (
    MouvementRefuse,
    decider_mutation,
    decider_signalement,
    mandats_a_clore,
)

# Président et Secrétaire national seulement (19/11/2026).
sanction_requise = permission_requise("mouvements.sanctionner")


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


@sanction_requise
def nouvelle_sanction(request, matricule):
    import datetime

    from apps.bureaux.views_bn import appliquer_ou_demander
    from apps.membres.models import Membre
    from apps.mouvements.forms import SanctionForm

    membre = get_object_or_404(Membre, matricule=matricule)
    form = SanctionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        champs = {
            k: (v.isoformat() if isinstance(v, datetime.date) else v)
            for k, v in form.cleaned_data.items()
        }
        try:
            appliquer_ou_demander(
                request,
                "sanction",
                {"membre": membre.matricule, "champs": champs},
                f"Sanction ({form.cleaned_data.get('type')}) pour {membre.nom_complet} "
                f"({membre.matricule}) : {form.cleaned_data.get('motif', '')[:120]}",
                succes="Sanction inscrite.",
            )
        except MouvementRefuse as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("membres:bn_fiche", matricule=matricule)
    return render(request, "mouvements/bn_sanction.html", {"membre": membre, "form": form})


@sanction_requise
def lever(request, pk):
    from apps.mouvements.models import Sanction

    sanction = get_object_or_404(Sanction.objects.select_related("membre"), pk=pk)
    if request.method != "POST":
        return redirect("membres:bn_fiche", matricule=sanction.membre.matricule)
    from apps.bureaux.views_bn import appliquer_ou_demander

    motif = request.POST.get("motif_levee", "")[:300]
    try:
        if not motif.strip():
            raise MouvementRefuse("Indiquez le motif de la levée.")
        appliquer_ou_demander(
            request,
            "lever",
            {"sanction": sanction.pk, "motif": motif},
            f"Lever la sanction « {sanction.libelle} » de {sanction.membre.nom_complet} : {motif}",
            succes="Sanction levée.",
        )
    except MouvementRefuse as exc:
        messages.error(request, str(exc))
    return redirect("membres:bn_fiche", matricule=sanction.membre.matricule)
