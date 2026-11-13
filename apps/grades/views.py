"""Pages du BNC : promouvoir, corriger le grade, promotions en série."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.grades.forms import CorrectionGradeForm, PromotionForm, SerieForm
from apps.grades.services import (
    GradeRefuse,
    corriger_grade,
    eligible,
    promouvoir,
    promouvoir_en_serie,
)
from apps.membres.grades import PAR_NOMINATION, Grade
from apps.membres.models import Membre, Statut
from apps.organisation.models import Region

gerer_membres = permission_required("membres.gerer_membres", raise_exception=True)


@login_required
@gerer_membres
def bn_promouvoir(request, matricule):
    membre = get_object_or_404(Membre, matricule=matricule)
    form = PromotionForm(request.POST or None, grade_actuel=membre.grade)
    if request.method == "POST" and form.is_valid():
        try:
            promouvoir(membre, par=request.user, **form.cleaned_data)
        except GradeRefuse as e:
            form.add_error(None, str(e))
        else:
            messages.success(request, "Grade enregistré.")
            return redirect("membres:bn_fiche", matricule=matricule)
    return render(request, "grades/promouvoir.html", {"membre": membre, "form": form})


@login_required
@gerer_membres
def bn_corriger(request, matricule):
    membre = get_object_or_404(Membre, matricule=matricule)
    form = CorrectionGradeForm(
        request.POST or None, initial={"grade": membre.grade, "date_effet": membre.date_grade}
    )
    if request.method == "POST" and form.is_valid():
        try:
            corriger_grade(membre, par=request.user, **form.cleaned_data)
        except GradeRefuse as e:
            form.add_error(None, str(e))
        else:
            messages.success(request, "Grade corrigé.")
            return redirect("membres:bn_fiche", matricule=matricule)
    return render(request, "grades/corriger.html", {"membre": membre, "form": form})


def _candidats(grade: int, region_pk: str | None):
    """Membres actifs pouvant recevoir `grade` : grade juste en dessous (1 à 6), inférieur (7+)."""
    qs = Membre.objects.filter(statut=Statut.ACTIF)
    if grade >= PAR_NOMINATION:
        qs = qs.filter(grade__lt=grade)
    else:
        qs = qs.filter(grade=grade - 1)
    if region_pk:
        qs = qs.filter(
            affectations__date_fin__isnull=True, affectations__paroisse__circuit__region=region_pk
        )
    return qs.order_by("nom", "prenoms")


@login_required
@gerer_membres
def bn_serie(request):
    try:
        grade = int(request.GET.get("grade", ""))
        Grade(grade)
    except ValueError:
        grade = None
    if grade == Grade.CAMARADE:
        grade = None
    region_pk = request.GET.get("region") or None
    if region_pk and not (region_pk.isdigit() and Region.objects.filter(pk=region_pk).exists()):
        region_pk = None
    candidats = list(_candidats(grade, region_pk)) if grade is not None else []
    aujourdhui = timezone.localdate()
    for m in candidats:
        m.est_eligible = eligible(m, aujourdhui) if grade < PAR_NOMINATION else True
    donnees = None
    if request.method == "POST":
        donnees = request.POST.copy()
        donnees["grade"] = str(grade) if grade is not None else ""  # le grade de la liste affichée
    form = SerieForm(donnees, initial={"grade": grade, "date_effet": aujourdhui})
    coches = set()
    if request.method == "POST" and form.is_valid():
        coches = {int(pk) for pk in request.POST.getlist("membres") if pk.isdigit()}
        choisis = [m for m in candidats if m.pk in coches]
        if not choisis:
            form.add_error(None, "Cochez au moins un membre.")
        else:
            try:
                faits = promouvoir_en_serie(choisis, par=request.user, **form.cleaned_data)
            except GradeRefuse as e:
                form.add_error(None, str(e))
            else:
                messages.success(request, f"{len(faits)} grade(s) enregistré(s).")
                suite = f"&region={region_pk}" if region_pk else ""
                return redirect(f"{request.path}?grade={grade}{suite}")
    return render(
        request,
        "grades/serie.html",
        {
            "form": form,
            "grade": grade,
            "grades": [(v, lib) for v, lib in Grade.choices if v > Grade.CAMARADE],
            "regions": Region.objects.order_by("code"),
            "region_pk": region_pk,
            "candidats": candidats,
            "coches": coches,
        },
    )


# --- Éligibles au grade visé, sessions de test ou d'examen, promotions spéciales, actes ---------


def _date(valeur):
    import datetime

    try:
        return datetime.date.fromisoformat(valeur or "")
    except ValueError:
        return None


def _grade_param(valeur):
    try:
        g = int(valeur)
        Grade(g)
    except (TypeError, ValueError):
        return None
    return g if g > Grade.CAMARADE else None


@login_required
@gerer_membres
def bn_eligibles(request):
    """Éligibles au grade VISÉ (ex. Capitaine → les Sous-Capitaines remplissant les conditions) ;
    on en fait une session de test ou d'examen."""
    from apps.grades.models import TypeEpreuve
    from apps.grades.services import creer_session, eligibles_au_grade

    grade = _grade_param(request.GET.get("grade") or request.POST.get("grade"))
    eligibles = list(eligibles_au_grade(grade, timezone.localdate())) if grade else []
    if request.method == "POST" and grade:
        pks = {int(x) for x in request.POST.getlist("membres") if x.isdigit()}
        try:
            s = creer_session(
                type_epreuve=request.POST.get("type", ""),
                date=_date(request.POST.get("date")) or timezone.localdate(),
                lieu=request.POST.get("lieu", ""),
                grade_vise=grade,
                membres=[m for m in eligibles if m.pk in pks],
                par=request.user,
            )
        except GradeRefuse as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Session créée ; les candidats sont notifiés.")
            return redirect("grades:bn_session", pk=s.pk)
    return render(
        request,
        "grades/eligibles.html",
        {
            "grade": grade,
            "grades": [(v, lib) for v, lib in Grade.choices if v > Grade.CAMARADE],
            "eligibles": eligibles,
            "par_nomination": grade is not None and grade >= PAR_NOMINATION,
            "types": TypeEpreuve.choices,
            "aujourdhui": timezone.localdate(),
        },
    )


@login_required
@gerer_membres
def bn_sessions(request):
    from apps.grades.models import SessionEpreuve

    return render(
        request,
        "grades/sessions.html",
        {"sessions": SessionEpreuve.objects.prefetch_related("candidats").select_related("acte")},
    )


@login_required
@gerer_membres
def bn_session(request, pk):
    from apps.grades.models import Resultat, SessionEpreuve
    from apps.grades.services import promouvoir_admis, saisir_resultats

    s = get_object_or_404(SessionEpreuve, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "resultats":
                resultats = {
                    int(k[1:]): v
                    for k, v in request.POST.items()
                    if k.startswith("r") and k[1:].isdigit()
                }
                n = saisir_resultats(s, resultats, par=request.user)
                messages.success(request, f"{n} résultat(s) enregistré(s).")
            elif action == "promouvoir":
                pks = {int(x) for x in request.POST.getlist("admis") if x.isdigit()}
                acte = promouvoir_admis(
                    s,
                    Membre.objects.filter(pk__in=pks),
                    numero=request.POST.get("numero", ""),
                    date_decision=_date(request.POST.get("date_decision")),
                    date_effet=_date(request.POST.get("date_effet")) or timezone.localdate(),
                    par=request.user,
                )
                messages.success(request, f"Promotions enregistrées : {acte}.")
        except GradeRefuse as e:
            messages.error(request, str(e))
        return redirect("grades:bn_session", pk=s.pk)
    return render(
        request,
        "grades/session.html",
        {
            "s": s,
            "candidats": s.candidats.select_related("membre"),
            "resultats": Resultat.choices,
            "aujourdhui": timezone.localdate(),
        },
    )


@login_required
@gerer_membres
def bn_speciales(request):
    """Promotion spéciale (art. 84) : un ou plusieurs membres, n'importe quel grade supérieur."""
    from apps.grades.models import ActePromotion, NatureActe
    from apps.grades.services import promotion_speciale

    if request.method == "POST":
        pks = {int(x) for x in request.POST.getlist("membres") if x.isdigit()}
        grade = _grade_param(request.POST.get("grade"))
        try:
            if grade is None:
                raise GradeRefuse("Choisissez le grade accordé.")
            acte = promotion_speciale(
                Membre.objects.filter(pk__in=pks),
                grade=grade,
                date_effet=_date(request.POST.get("date_effet")) or timezone.localdate(),
                numero=request.POST.get("numero", ""),
                date_decision=_date(request.POST.get("date_decision")),
                motif=request.POST.get("motif", ""),
                par=request.user,
            )
        except GradeRefuse as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Promotion spéciale enregistrée : {acte}.")
            return redirect("grades:bn_speciales")
    return render(
        request,
        "grades/speciales.html",
        {
            "grades": [(v, lib) for v, lib in Grade.choices if v > Grade.CAMARADE],
            "actes": ActePromotion.objects.filter(nature=NatureActe.SPECIALE),
            "aujourdhui": timezone.localdate(),
        },
    )


@login_required
@gerer_membres
def recherche(request):
    """Recherche d'un membre (matricule ou nom), réponse JSON, BN seulement."""
    from django.http import JsonResponse

    from apps.evenements.services import rechercher_membres

    return JsonResponse(
        {
            "resultats": [
                {
                    "pk": m.pk,
                    "nom": m.nom_complet,
                    "matricule": m.matricule,
                    "paroisse": m.affectation_actuelle.paroisse.nom
                    if m.affectation_actuelle
                    else "",
                }
                for m in rechercher_membres(request.GET.get("q", ""))
            ]
        }
    )


@login_required
@gerer_membres
def bn_actes(request):
    from apps.grades.models import ActePromotion

    return render(
        request,
        "grades/actes.html",
        {"actes": ActePromotion.objects.prefetch_related("promotions", "sessions")},
    )


def _pdf(contenu: bytes, nom: str):
    from django.http import HttpResponse

    r = HttpResponse(contenu, content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="{nom}"'
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
@gerer_membres
def acte_pdf_vue(request, pk):
    from apps.grades.models import ActePromotion
    from apps.grades.pdf import acte_pdf

    acte = get_object_or_404(ActePromotion, pk=pk)
    return _pdf(acte_pdf(acte), f"decision-{acte.pk}.pdf")


@login_required
def extrait_pdf(request, pk):
    """Extrait de l'acte pour un promu : le membre lui-même ou le BN."""
    from django.http import Http404

    from apps.grades.models import ActePromotion
    from apps.grades.pdf import acte_pdf

    acte = get_object_or_404(ActePromotion, pk=pk)
    matricule = request.GET.get("matricule", "")
    membre = Membre.objects.filter(matricule=matricule).first()
    if membre is None or not acte.promotions.filter(membre=membre).exists():
        raise Http404
    soi = membre.compte_id == request.user.pk
    if not (soi or request.user.has_perm("membres.gerer_membres")):
        raise Http404
    return _pdf(acte_pdf(acte, seulement=membre), f"extrait-{membre.matricule}.pdf")
