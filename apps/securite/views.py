import time

import segno
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.journal.models import DOUBLE_VERIFICATION
from apps.journal.services import journaliser
from apps.securite.models import DoubleVerification
from apps.securite.services import (
    ECHECS_MAX,
    SESSION_ECHECS,
    SESSION_OK,
    SESSION_SECRET,
    doit_verifier,
    double_verification_active,
)
from apps.securite.totp import nouveau_secret, uri_provisioning, verifier


def _suivant(request) -> str:
    suivant = request.POST.get("suivant") or request.GET.get("suivant") or "/"
    if not url_has_allowed_host_and_scheme(suivant, {request.get_host()}):
        return "/"
    return suivant


def _ouvrir(request, dv: DoubleVerification, pas: int) -> None:
    dv.dernier_pas = pas
    dv.save(update_fields=["dernier_pas", "secret", "active", "date_activation"])
    request.session[SESSION_OK] = request.user.pk
    request.session.pop(SESSION_ECHECS, None)
    request.session.pop(SESSION_SECRET, None)


def _echec(request) -> bool:
    """Compte un code faux ; True si la limite est atteinte (session fermée)."""
    echecs = request.session.get(SESSION_ECHECS, 0) + 1
    request.session[SESSION_ECHECS] = echecs
    journaliser(request.user, DOUBLE_VERIFICATION, evenement="code_faux", essai=echecs)
    if echecs >= ECHECS_MAX:
        journaliser(request.user, DOUBLE_VERIFICATION, evenement="deconnexion_apres_echecs")
        logout(request)
        messages.error(request, "Trop de codes erronés : reconnectez-vous.")
        return True
    return False


@login_required
def activer(request):
    if not doit_verifier(request.user):
        return redirect("/")
    if double_verification_active(request.user):
        return redirect("securite:code")
    secret = request.session.get(SESSION_SECRET) or nouveau_secret()
    request.session[SESSION_SECRET] = secret
    erreur = None
    if request.method == "POST":
        pas = verifier(secret, request.POST.get("code", ""), time.time(), None)
        if pas is None:
            erreur = "Code incorrect. Vérifiez l'heure de votre téléphone et réessayez."
            if _echec(request):
                return redirect("connexion")
        else:
            dv, _ = DoubleVerification.objects.get_or_create(compte=request.user)
            dv.secret, dv.active, dv.date_activation = secret, True, timezone.now()
            _ouvrir(request, dv, pas)
            journaliser(request.user, DOUBLE_VERIFICATION, evenement="activation")
            messages.success(request, "Double vérification activée.")
            return redirect(_suivant(request))
    uri = uri_provisioning(secret, request.user.identifiant)
    return render(
        request,
        "securite/activer.html",
        {
            "qr": segno.make(uri, error="m").svg_inline(scale=5, dark="#14284B"),
            "cle": " ".join(secret[i : i + 4] for i in range(0, len(secret), 4)),
            "erreur": erreur,
            "suivant": _suivant(request),
        },
    )


@login_required
def code(request):
    if not doit_verifier(request.user):
        return redirect("/")
    dv = DoubleVerification.objects.filter(compte=request.user, active=True).first()
    if dv is None:
        return redirect("securite:activer")
    erreur = None
    if request.method == "POST":
        pas = verifier(dv.secret, request.POST.get("code", ""), time.time(), dv.dernier_pas)
        if pas is None:
            erreur = "Code incorrect ou déjà utilisé."
            if _echec(request):
                return redirect("connexion")
        else:
            _ouvrir(request, dv, pas)
            journaliser(request.user, DOUBLE_VERIFICATION, evenement="code_correct")
            return redirect(_suivant(request))
    return render(request, "securite/code.html", {"erreur": erreur, "suivant": _suivant(request)})
