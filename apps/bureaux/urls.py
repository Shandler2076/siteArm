from django.urls import path

from apps.bureaux import views, views_bn

app_name = "bureaux"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("bn/installer/", views_bn.installer, name="bn_installer"),
    path("bn/fonctions/", views_bn.fonctions, name="bn_fonctions"),
    path("bn/echeances/", views_bn.echeances, name="bn_echeances"),
    path("<str:cle>/membres/", views.membres, name="membres"),
    path("<str:cle>/membres/<str:matricule>/", views.fiche_membre, name="fiche_membre"),
    path("<str:cle>/anciens/", views.anciens, name="anciens"),
    path(
        "<str:cle>/membres/<str:matricule>/reinitialiser/",
        views.reinitialiser,
        name="reinitialiser",
    ),
]
