from collections import Counter
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.lots.controle import controler_lot, creer_lot, remplacer_fichier
from apps.lots.forms import FormulaireDepot, FormulaireLigne, FormulaireRedepot, _affichage
from apps.lots.generation import GenerationEchouee, valider_lot
from apps.lots.lecture import FichierInvalide
from apps.lots.modele_excel import modele_pour_region
from apps.lots.models import EtatLigne, EtatLot, LigneLot, Lot
from apps.lots.pdf import TRANCHE
from apps.membres.models import Categorie
from apps.membres.stockage import stockage_prive
from apps.organisation.models import Paroisse, Region

TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def bn_requis(vue):
    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not request.user.has_perm("membres.gerer_membres"):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


@bn_requis
def modele(request, code):
    region = get_object_or_404(Region, code=code, active=True)
    r = HttpResponse(modele_pour_region(region), content_type=TYPE_XLSX)
    r["Content-Disposition"] = f'attachment; filename="modele-membres-region-{region.code}.xlsx"'
    return r


# --- Lots : liste, dépôt, contrôle -------------------------------------------------------


def _lot_modifiable(pk) -> Lot:
    """Lot verrouillé en brouillon. À appeler dans une transaction."""
    lot = get_object_or_404(Lot.objects.select_for_update(), pk=pk)
    if lot.etat != EtatLot.BROUILLON:
        raise PermissionDenied("Ce lot est validé : il ne peut plus être modifié.")
    return lot


@bn_requis
def liste(request):
    lots = Lot.objects.select_related("region").annotate(nb=Count("lignes"))
    regions = Region.objects.filter(active=True).order_by("code")
    return render(request, "lots/liste.html", {"lots": lots, "regions": regions})


@bn_requis
def deposer(request):
    form = FormulaireDepot(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            lot = creer_lot(
                region=form.cleaned_data["region"],
                fichier=form.cleaned_data["fichier"],
                par=request.user,
            )
        except FichierInvalide as e:
            form.add_error("fichier", str(e))
        else:
            return redirect("lots:controle", pk=lot.pk)
    return render(request, "lots/deposer.html", {"form": form})


def _comprise(ligne: LigneLot, noms_paroisses: dict) -> dict:
    """Valeurs telles que le site les a comprises (sinon telles que lues)."""
    d, b = ligne.donnees or {}, ligne.brutes or {}
    date = d.get("date_naissance")
    if date:
        date = f"{date[8:10]}/{date[5:7]}/{date[0:4]}"
    else:
        brut = b.get("Date de naissance")
        date = "" if brut is None else _affichage(brut)
    categories = dict(Categorie.choices)
    return {
        "nom": " ".join(
            str(x or "")
            for x in (d.get("nom") or b.get("Nom*"), d.get("prenoms") or b.get("Prénoms*"))
        ),
        "sexe": d.get("sexe") or b.get("Sexe*") or "",
        "date": date,
        "paroisse": noms_paroisses.get(d.get("paroisse_integration"))
        or b.get("Paroisse d'intégration*")
        or "",
        "annee": d.get("annee_integration") or b.get("Année d'intégration*") or "",
        "categorie": categories.get(d.get("categorie"), b.get("Catégorie") or ""),
    }


def _resume(lot: Lot) -> dict:
    lignes = list(lot.lignes.select_related("membre"))
    retenues = [x for x in lignes if x.etat in (EtatLigne.CORRECTE, EtatLigne.GARDEE)]
    paroisses = dict(
        Paroisse.objects.filter(
            pk__in={x.donnees.get("paroisse_integration") for x in retenues}
        ).values_list("pk", "nom")
    )
    tous_pk = {x.donnees.get("paroisse_integration") for x in lignes}
    noms = dict(Paroisse.objects.filter(pk__in=tous_pk).values_list("pk", "nom"))
    return {
        "lignes": lignes,
        "affichage": {x.pk: _comprise(x, noms) for x in lignes},
        "par_etat": [
            (lib, sum(1 for x in lignes if x.etat == val)) for val, lib in EtatLigne.choices
        ],
        "par_annee": sorted(Counter(x.donnees.get("annee_integration") for x in retenues).items()),
        "par_paroisse": sorted(
            Counter(
                paroisses.get(x.donnees.get("paroisse_integration"), "—") for x in retenues
            ).items()
        ),
        "nb_retenues": len(retenues),
    }


@bn_requis
def controle(request, pk):
    lot = get_object_or_404(Lot.objects.select_related("region"), pk=pk)
    form = FormulaireRedepot(request.POST or None, request.FILES or None)
    if request.method == "POST":
        with transaction.atomic():
            _lot_modifiable(pk)
        if form.is_valid():
            try:
                remplacer_fichier(lot, form.cleaned_data["fichier"], request.user)
            except ValueError as e:  # FichierInvalide, ou lot validé entre-temps
                form.add_error("fichier", str(e))
            else:
                messages.success(request, "Nouveau fichier déposé et vérifié.")
                return redirect("lots:controle", pk=lot.pk)
    contexte = {"lot": lot, "form": form, **_resume(lot)}
    return render(request, "lots/controle.html", contexte)


@bn_requis
def ligne(request, pk, numero):
    lot = get_object_or_404(Lot, pk=pk)
    l_ = get_object_or_404(LigneLot, lot=lot, numero=numero)
    form = FormulaireLigne(request.POST or None, brutes=l_.brutes)
    if request.method == "POST":
        with transaction.atomic():
            lot = _lot_modifiable(pk)
            if form.is_valid():
                l_ = LigneLot.objects.get(lot=lot, numero=numero)
                l_.brutes = form.brutes()
                l_.corrigee_par = request.user
                l_.date_correction = timezone.now()
                if l_.etat == EtatLigne.ECARTEE:
                    l_.etat = EtatLigne.CORRECTE
                l_.save(update_fields=["brutes", "corrigee_par", "date_correction", "etat"])
        if form.is_valid():
            controler_lot(lot)
            messages.success(request, f"Ligne {numero} corrigée et vérifiée.")
            return redirect("lots:controle", pk=lot.pk)
    return render(request, "lots/ligne.html", {"lot": lot, "ligne": l_, "form": form})


@bn_requis
@require_POST
def action_ligne(request, pk, numero, action):
    with transaction.atomic():
        lot = _lot_modifiable(pk)
        l_ = get_object_or_404(LigneLot, lot=lot, numero=numero)
        if action == "ecarter":
            l_.etat = EtatLigne.ECARTEE
        elif action == "reprendre" and l_.etat == EtatLigne.ECARTEE:
            l_.etat = EtatLigne.CORRECTE
        elif action == "garder" and l_.etat == EtatLigne.DOUBLON:
            l_.etat = EtatLigne.GARDEE
        else:
            return HttpResponseBadRequest("Action impossible sur cette ligne.")
        l_.save(update_fields=["etat"])
    if action == "reprendre":
        controler_lot(lot)
    return redirect(f"{reverse('lots:controle', args=[lot.pk])}#ligne-{numero}")


@bn_requis
def confirmer(request, pk):
    lot = get_object_or_404(Lot.objects.select_related("region"), pk=pk)
    erreur = None
    if request.method == "POST":
        if lot.etat != EtatLot.BROUILLON:
            raise PermissionDenied("Ce lot est déjà validé.")
        if request.POST.get("confirme") != "on":
            erreur = "Cochez la case pour confirmer."
        else:
            try:
                valider_lot(lot, request.user)
            except GenerationEchouee as e:
                messages.error(request, str(e))
                return redirect("lots:controle", pk=lot.pk)
            messages.success(request, f"Lot n° {lot.pk} validé : les membres sont créés.")
            return redirect("lots:resultat", pk=lot.pk)
    return render(request, "lots/confirmer.html", {"lot": lot, "erreur": erreur, **_resume(lot)})


@bn_requis
def resultat(request, pk):
    lot = get_object_or_404(Lot.objects.select_related("region"), pk=pk, etat=EtatLot.VALIDE)
    lignes = list(
        lot.lignes.filter(membre__isnull=False).select_related(
            "membre", "membre__paroisse_integration"
        )
    )
    n = len(lignes)
    tranches = [(d, min(d + TRANCHE - 1, n)) for d in range(1, n + 1, TRANCHE)]
    return render(
        request, "lots/resultat.html", {"lot": lot, "lignes": lignes, "tranches": tranches}
    )


@bn_requis
def fichier_depose(request, pk, index):
    lot = get_object_or_404(Lot, pk=pk)
    if index >= len(lot.fichiers):
        raise Http404
    infos = lot.fichiers[index]
    r = FileResponse(
        stockage_prive.open(infos["chemin"], "rb"),
        as_attachment=True,
        filename=infos["nom"],
        content_type=TYPE_XLSX,
    )
    r["Cache-Control"] = "private, no-store"
    return r


def _pdf(contenu: bytes, nom: str) -> HttpResponse:
    r = HttpResponse(contenu, content_type="application/pdf")
    r["Content-Disposition"] = f'attachment; filename="{nom}"'
    r["Cache-Control"] = "private, no-store"
    return r


@bn_requis
@require_POST
def fiches(request, pk):
    from apps.lots.pdf import fiches_du_lot_pdf

    lot = get_object_or_404(Lot, pk=pk, etat=EtatLot.VALIDE)
    debut = (
        int(request.POST.get("debut") or 1) if (request.POST.get("debut") or "1").isdigit() else 1
    )
    fin = request.POST.get("fin")
    fin = int(fin) if fin and fin.isdigit() else None
    contenu = fiches_du_lot_pdf(lot, request.user, debut=debut, fin=fin)
    return _pdf(contenu, f"fiches-lot-{lot.pk}-{debut}.pdf")


@bn_requis
def recapitulatif(request, pk):
    from apps.lots.pdf import recapitulatif_pdf

    lot = get_object_or_404(Lot.objects.select_related("region"), pk=pk, etat=EtatLot.VALIDE)
    return _pdf(recapitulatif_pdf(lot), f"recapitulatif-lot-{lot.pk}.pdf")
