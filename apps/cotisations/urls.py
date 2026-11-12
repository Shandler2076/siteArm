from django.urls import path

from apps.cotisations import views

app_name = "cotisations"
urlpatterns = [
    path("versement/<int:pk>/annuler/", views.annuler_versement, name="annuler"),
    path("moi/", views.mes_cotisations, name="moi"),
    path("moi/etat.pdf", views.mon_etat_pdf, name="mon_etat_pdf"),
    path("membre/<str:matricule>/etat.pdf", views.etat_membre_pdf, name="etat_membre_pdf"),
    path("recu/<int:pk>.pdf", views.recu, name="recu"),
    path("<str:cle>/", views.accueil, name="accueil"),
    path("<str:cle>/grille/", views.grille, name="grille"),
    path("<str:cle>/versement/", views.versement, name="versement"),
    path("<str:cle>/a-valider/", views.a_valider, name="a_valider"),
    path("<str:cle>/parts/", views.parts, name="parts"),
]
