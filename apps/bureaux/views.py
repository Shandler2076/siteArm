from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.bureaux.perimetre import (
    anciens_membres,
    est_bn,
    membres_visibles,
    unite_depuis_cle,
    unites_gerees,
    unites_verification,
)
from apps.membres.verification import MOTIFS, carte_de


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
    from apps.journal.models import CONSULTATION_FICHE
    from apps.journal.services import journaliser
    from apps.membres.rubriques import contexte_rubriques
    from apps.mouvements.views import contexte_fiche

    journaliser(request.user, CONSULTATION_FICHE, unite=unite.cle, membre=membre.matricule)

    return render(
        request,
        "bureaux/fiche_membre.html",
        {
            "unite": unite,
            "membre": membre,
            "parcours": parcours,
            "mandats": mandats,
            **contexte_fiche(unite, membre),
            **contexte_rubriques(request, membre, avec_evenements=unite.niveau == "national"),
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


@login_required
@require_POST
def reinitialiser(request, cle, matricule):
    from apps.bureaux.services import reinitialiser_mot_de_passe
    from apps.membres.views_bn import _reponse_pdf

    unite = unite_depuis_cle(request.user, cle)
    membre = membres_visibles(unite).filter(matricule=matricule).first()
    if membre is None:
        raise Http404
    if unite.niveau != "paroisse" and not est_bn(request.user):
        raise PermissionDenied
    return _reponse_pdf(reinitialiser_mot_de_passe(cible=membre, par=request.user), matricule)


class VerifierForm(forms.Form):
    matricule = forms.CharField(
        label="Matricule exact", max_length=20, help_text="Ex. 2015-01AS-0157 (pas de nom)."
    )
    motif = forms.ChoiceField(
        label="Motif de la vérification", choices=[("", "— Choisir —"), *MOTIFS]
    )
    precision = forms.CharField(label="Précision du motif", max_length=200, required=False)

    def clean(self):
        d = super().clean()
        if d.get("motif") == "autre" and not d.get("precision", "").strip():
            self.add_error("precision", "Précisez le motif.")
        return d


@login_required
def verifier(request):
    """Carte d'identité réduite d'un membre, par matricule exact et avec motif (journalisé)."""
    unites = unites_verification(request.user)
    if not unites:
        raise PermissionDenied
    form = VerifierForm(request.POST or None)
    carte, introuvable = None, False
    if request.method == "POST" and form.is_valid():
        from apps.journal.models import VERIFICATION_MEMBRE
        from apps.journal.services import journaliser

        d = form.cleaned_data
        carte = carte_de(d["matricule"])
        details = {"motif": d["motif"], "precision": d.get("precision", "").strip()}
        if carte is None:
            introuvable = True
            details["saisi"] = d["matricule"][:20]
        else:
            details["membre"] = carte.matricule
        journaliser(request.user, VERIFICATION_MEMBRE, unite=unites[0].cle, **details)
    return render(
        request,
        "bureaux/verifier.html",
        {"form": form, "carte": carte, "introuvable": introuvable},
    )
