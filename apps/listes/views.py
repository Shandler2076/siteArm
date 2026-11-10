from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.bureaux.perimetre import unite_depuis_cle
from apps.bureaux.views_bn import bn_requis
from apps.journal.models import LISTE_EXCEL, LISTE_PDF, STATISTIQUES_PDF, TRANCHES_AGE
from apps.journal.services import journaliser
from apps.listes.ages import tranches_depuis_bornes
from apps.listes.colonnes import COLONNES_LISTE, lignes, preparer
from apps.listes.exports import liste_excel, liste_pdf, statistiques_pdf
from apps.listes.filtres import FiltreListeForm, membres_filtres, resume_filtres
from apps.listes.forms import BornesForm
from apps.listes.models import ReglageStatistiques
from apps.listes.statistiques import calculer_statistiques
from apps.membres.models import Statut

PAR_PAGE = 100


def _sans_page(request) -> str:
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


@login_required
def liste(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    aujourdhui = timezone.localdate()
    form = FiltreListeForm(unite, request.GET)
    contexte = {"unite": unite, "form": form, "page": None, "requete": _sans_page(request)}
    if form.is_valid():
        colonnes = form.cleaned_data["colonnes"]
        qs = preparer(membres_filtres(unite, form.cleaned_data, aujourdhui), aujourdhui)
        page = Paginator(qs, PAR_PAGE).get_page(request.GET.get("page"))
        contexte.update(
            page=page,
            entetes=[COLONNES_LISTE[c][0] for c in colonnes],
            rangees=list(lignes(page.object_list, colonnes, aujourdhui)),
            resume=resume_filtres(form),
        )
    return render(request, "listes/liste.html", contexte)


def _statuts(request) -> list[str]:
    """Actif par défaut ; après envoi du formulaire, les statuts cochés (aucun = tous)."""
    if not request.GET.get("envoye"):
        return [Statut.ACTIF]
    valides = set(Statut.values)
    return [s for s in request.GET.getlist("statut") if s in valides]


def _sections(request, unite):
    statuts = _statuts(request)
    sections = calculer_statistiques(unite, statuts, timezone.localdate())
    base = reverse("listes:liste", args=[unite.cle])
    for section in sections:
        for c in section.cellules:
            c.lien = base + "?" + urlencode(c.filtres, doseq=True)
    return statuts, sections


@login_required
def statistiques(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    statuts, sections = _sections(request, unite)
    return render(
        request,
        "listes/statistiques.html",
        {
            "unite": unite,
            "sections": sections,
            "statuts": statuts,
            "choix_statuts": Statut.choices,
            "requete": request.GET.urlencode(),
        },
    )


@login_required
def statistiques_pdf_vue(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    statuts, sections = _sections(request, unite)
    contenu = statistiques_pdf(unite, sections, statuts)
    journaliser(request.user, STATISTIQUES_PDF, unite=unite.cle, statuts=statuts)
    horodatage = timezone.localtime().strftime("%Y%m%d-%H%M")
    return telechargement(contenu, "application/pdf", f"statistiques-{cle}-{horodatage}.pdf")


TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def telechargement(contenu: bytes, type_mime: str, nom: str) -> HttpResponse:
    r = HttpResponse(contenu, content_type=type_mime)
    r["Content-Disposition"] = f'attachment; filename="{nom}"'
    r["Cache-Control"] = "private, no-store"
    return r


def _export(request, cle, fabrique, action, extension, type_mime):
    unite = unite_depuis_cle(request.user, cle)
    form = FiltreListeForm(unite, request.GET)
    if not form.is_valid():
        return redirect(reverse("listes:liste", args=[cle]) + "?" + request.GET.urlencode())
    contenu, total = fabrique(unite, form, timezone.localdate())
    journaliser(
        request.user, action, unite=unite.cle, lignes=total, filtres=request.GET.urlencode()
    )
    horodatage = timezone.localtime().strftime("%Y%m%d-%H%M")
    return telechargement(contenu, type_mime, f"liste-{cle}-{horodatage}.{extension}")


@login_required
def liste_pdf_vue(request, cle):
    return _export(request, cle, liste_pdf, LISTE_PDF, "pdf", "application/pdf")


@login_required
def liste_excel_vue(request, cle):
    return _export(request, cle, liste_excel, LISTE_EXCEL, "xlsx", TYPE_XLSX)


@bn_requis
def tranches(request):
    reglage = ReglageStatistiques.courant()
    form = BornesForm(request.POST or None, initial={"bornes": reglage.bornes.replace(",", ", ")})
    if request.method == "POST" and form.is_valid():
        avant, apres = reglage.bornes, form.cleaned_data["bornes"]
        reglage.bornes = apres
        reglage.save(update_fields=["bornes"])
        journaliser(request.user, TRANCHES_AGE, avant=avant, apres=apres)
        messages.success(request, "Tranches d'âge enregistrées.")
        return redirect("listes:tranches")
    return render(
        request,
        "listes/tranches.html",
        {"form": form, "tranches": tranches_depuis_bornes(reglage.liste_bornes)},
    )
