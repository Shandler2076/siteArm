from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.bureaux.perimetre import unite_depuis_cle
from apps.journal.models import LISTE_EXCEL, LISTE_PDF
from apps.journal.services import journaliser
from apps.listes.colonnes import COLONNES_LISTE, lignes, preparer
from apps.listes.exports import liste_excel, liste_pdf
from apps.listes.filtres import FiltreListeForm, membres_filtres, resume_filtres

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


@login_required
def statistiques(request, cle):
    unite = unite_depuis_cle(request.user, cle)
    return render(request, "listes/statistiques.html", {"unite": unite, "sections": []})


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
