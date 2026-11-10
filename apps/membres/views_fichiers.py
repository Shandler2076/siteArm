"""Service des fichiers privés : chaque accès vérifie les droits. Sinon : 404."""

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from apps.membres.models import Membre, PhotoIdentite


def _fichier(champ, nom):
    if not champ:
        raise Http404
    r = FileResponse(champ.open("rb"), content_type="image/jpeg", filename=nom)
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
def photo(request, pk):
    p = get_object_or_404(PhotoIdentite.objects.select_related("membre"), pk=pk)
    proprietaire = p.membre.compte_id == request.user.pk
    if not (proprietaire or request.user.has_perm("membres.gerer_membres")):
        raise Http404
    return _fichier(p.fichier, f"photo-{p.membre.matricule}.jpg")


@login_required
def cip(request, matricule):
    if not request.user.has_perm("membres.voir_cip"):
        raise Http404
    m = get_object_or_404(Membre, matricule=matricule)
    return _fichier(m.photo_cip, f"cip-{m.matricule}")
