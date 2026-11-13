from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.notifications.services import resoudre_lien


@login_required
def liste(request):
    notifications = list(request.user.notifications.all()[:100])
    return render(request, "notifications/liste.html", {"notifications": notifications})


@login_required
def ouvrir(request, pk):
    """Clic sur une notification : marquée lue, puis la page concernée (si on y a droit)."""
    n = get_object_or_404(request.user.notifications, pk=pk)
    if not n.lue:
        n.lue = True
        n.save(update_fields=["lue"])
    cible = resoudre_lien(request.user, n.lien)
    if cible is None:
        messages.info(request, n.message)
        return redirect("notifications:liste")
    return redirect(cible)


@login_required
@require_POST
def tout_lu(request):
    request.user.notifications.filter(lue=False).update(lue=True)
    return redirect("notifications:liste")
