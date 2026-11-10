from django.contrib.auth import views as auth_views
from django.urls import path

from apps.comptes import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("connexion/", views.Connexion.as_view(), name="connexion"),
    path(
        "mot-de-passe/changer/", views.ChangerMotDePasse.as_view(), name="changer_mot_de_passe"
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
]
