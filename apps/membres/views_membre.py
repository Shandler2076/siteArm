from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from apps.membres.forms import FormulaireCoordonnees, FormulairePhoto
from apps.membres.models import EtatPhoto, Membre, PhotoIdentite
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


@login_required
def ma_photo(request):
    membre = membre_de(request)
    form = FormulairePhoto(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            for ancienne in membre.photos.filter(etat=EtatPhoto.EN_ATTENTE):
                ancienne.fichier.delete(save=False)
                PhotoIdentite.objects.filter(pk=ancienne.pk).delete()
            photo = PhotoIdentite(membre=membre)
            photo.fichier.save(f"{membre.matricule}.jpg", form.cleaned_data["fichier"], save=False)
            photo.save()
        messages.success(request, "Photo envoyée. Elle sera visible après validation par le BN.")
        return redirect("membres:ma_fiche")
    return render(request, "membres/ma_photo.html", {"form": form, "membre": membre})
