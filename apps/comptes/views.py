from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.comptes.forms import FormulaireConnexion


class Connexion(auth_views.LoginView):
    template_name = "comptes/connexion.html"
    authentication_form = FormulaireConnexion
    redirect_authenticated_user = True


@login_required
def accueil(request):
    return render(request, "accueil.html")
