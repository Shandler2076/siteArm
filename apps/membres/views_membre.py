from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from apps.membres.forms import FormulaireCoordonnees
from apps.membres.models import Membre
from apps.membres.pdf import fiche_identification_pdf


def membre_de(request) -> Membre:
    try:
        return request.user.membre
    except Membre.DoesNotExist as e:
        raise Http404("Ce compte n'est pas rattaché à un membre.") from e


@login_required
def ma_fiche(request):
    membre = membre_de(request)
    parcours = membre.affectations.select_related("paroisse", "circuit_a_date", "region_a_date")
    photo_en_attente = membre.photos.filter(etat="en_attente").first()
    return render(request, "membres/ma_fiche.html", {
        "membre": membre, "parcours": parcours, "photo_en_attente": photo_en_attente,
    })


@login_required
def mes_coordonnees(request):
    membre = membre_de(request)
    form = FormulaireCoordonnees(request.POST or None, instance=membre)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vos coordonnées ont été mises à jour.")
        return redirect("membres:ma_fiche")
    return render(request, "membres/mes_coordonnees.html", {"form": form})


@login_required
def ma_fiche_pdf(request):
    membre = membre_de(request)
    r = HttpResponse(fiche_identification_pdf(membre), content_type="application/pdf")
    r["Content-Disposition"] = f'attachment; filename="fiche-{membre.matricule}.pdf"'
    r["Cache-Control"] = "private, no-store"
    return r
