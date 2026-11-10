from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy

from apps.comptes.forms import FormulaireConnexion


class Connexion(auth_views.LoginView):
    template_name = "comptes/connexion.html"
    authentication_form = FormulaireConnexion
    redirect_authenticated_user = True


@login_required
def accueil(request):
    return render(request, "accueil.html")


class ChangerMotDePasse(auth_views.PasswordChangeView):
    template_name = "comptes/changer_mot_de_passe.html"
    success_url = reverse_lazy("accueil")

    def form_valid(self, form):
        reponse = super().form_valid(form)
        self.request.user.doit_changer_mot_de_passe = False
        self.request.user.save(update_fields=["doit_changer_mot_de_passe"])
        messages.success(self.request, "Votre mot de passe a été changé.")
        return reponse
