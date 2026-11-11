from django.urls import path

from apps.mouvements import views, views_bn

app_name = "mouvements"

urlpatterns = [
    path("bn/decisions/", views_bn.decisions, name="bn_decisions"),
    path("bn/mutations/<int:pk>/", views_bn.mutation, name="bn_mutation"),
    path("bn/signalements/<int:pk>/", views_bn.signalement, name="bn_signalement"),
    path("mutations/<int:pk>/", views.mutation_aiguillage, name="mutation_aiguillage"),
    path("<str:cle>/demandes/", views.demandes, name="demandes"),
    path("<str:cle>/mutations/nouvelle/", views.nouvelle_mutation, name="nouvelle_mutation"),
    path("<str:cle>/mutations/<int:pk>/", views.mutation, name="mutation"),
    path("<str:cle>/mutations/<int:pk>/avis/", views.avis, name="avis"),
    path(
        "<str:cle>/membres/<str:matricule>/signaler/<str:type_signalement>/",
        views.signaler_vue,
        name="signaler",
    ),
]
