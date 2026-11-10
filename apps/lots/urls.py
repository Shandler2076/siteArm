from django.urls import path

from apps.lots import views

app_name = "lots"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.deposer, name="deposer"),
    path("modele/<str:code>.xlsx", views.modele, name="modele"),
    path("<int:pk>/", views.controle, name="controle"),
    path("<int:pk>/confirmer/", views.confirmer, name="confirmer"),
    path("<int:pk>/resultat/", views.resultat, name="resultat"),
    path("<int:pk>/fiches.pdf", views.fiches, name="fiches"),
    path("<int:pk>/recapitulatif.pdf", views.recapitulatif, name="recapitulatif"),
    path("<int:pk>/lignes/<int:numero>/", views.ligne, name="ligne"),
    path("<int:pk>/lignes/<int:numero>/<str:action>/", views.action_ligne, name="action_ligne"),
]
