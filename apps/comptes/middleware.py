from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ChangementMotDePasseObligatoire:
    """Tant que le mot de passe provisoire n'est pas changé, toute page renvoie au changement."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.doit_changer_mot_de_passe:
            autorises = (reverse("changer_mot_de_passe"), reverse("deconnexion"))
            chemin = request.path
            if chemin not in autorises and not chemin.startswith("/" + settings.STATIC_URL):
                return redirect("changer_mot_de_passe")
        return self.get_response(request)
