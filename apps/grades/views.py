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
    candidats = list(_candidats(grade, region_pk)) if grade is not None else []
    aujourdhui = timezone.localdate()
    for m in candidats:
        m.est_eligible = eligible(m, aujourdhui) if grade < PAR_NOMINATION else True
    form = SerieForm(request.POST or None, initial={"grade": grade, "date_effet": aujourdhui})
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
                return redirect(f"{request.path}?grade={grade}")
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
