from django.urls import path

from apps.mouvements import views

app_name = "mouvements"

urlpatterns = [
    path("mutations/<int:pk>/", views.mutation_aiguillage, name="mutation_aiguillage"),
    path("<str:cle>/demandes/", views.demandes, name="demandes"),
    path("<str:cle>/mutations/nouvelle/", views.nouvelle_mutation, name="nouvelle_mutation"),
    path("<str:cle>/mutations/<int:pk>/", views.mutation, name="mutation"),
    path("<str:cle>/mutations/<int:pk>/avis/", views.avis, name="avis"),
]
