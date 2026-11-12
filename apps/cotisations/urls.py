from django.urls import path

from apps.cotisations import views

app_name = "cotisations"
urlpatterns = [
    path("versement/<int:pk>/annuler/", views.annuler_versement, name="annuler"),
    path("<str:cle>/", views.accueil, name="accueil"),
    path("<str:cle>/grille/", views.grille, name="grille"),
    path("<str:cle>/versement/", views.versement, name="versement"),
    path("<str:cle>/a-valider/", views.a_valider, name="a_valider"),
    path("<str:cle>/parts/", views.parts, name="parts"),
]
