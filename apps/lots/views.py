from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.lots.modele_excel import modele_pour_region
from apps.organisation.models import Region

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
