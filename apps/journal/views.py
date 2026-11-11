import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from apps.bureaux.views_bn import bn_requis
from apps.journal.models import LIBELLES, EntreeJournal


def _date(valeur: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return None


@bn_requis
def liste(request):
    qs = EntreeJournal.objects.select_related("auteur")
    g = request.GET
    action = g.get("action", "")
    if action:
        qs = qs.filter(action=action)
    auteur = g.get("auteur", "").strip()
    if auteur:
        qs = qs.filter(auteur__identifiant__iexact=auteur)
    q = g.get("q", "").strip()
    if q:
        qs = qs.filter(Q(unite__icontains=q) | Q(details__icontains=q))
    du, au = _date(g.get("du")), _date(g.get("au"))
    if du:
        qs = qs.filter(date__date__gte=du)
    if au:
        qs = qs.filter(date__date__lte=au)
    page = Paginator(qs, 50).get_page(g.get("page"))
    requete = g.copy()
    requete.pop("page", None)
    return render(
        request,
        "journal/liste.html",
        {
            "page": page,
            "actions": sorted(LIBELLES.items(), key=lambda x: x[1]),
            "filtres": {
                "action": action,
                "auteur": auteur,
                "q": q,
                "du": g.get("du", ""),
                "au": g.get("au", ""),
            },
            "requete": requete.urlencode(),
        },
    )
