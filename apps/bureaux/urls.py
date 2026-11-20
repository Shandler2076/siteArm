from django.urls import path

from apps.bureaux import views, views_bn

app_name = "bureaux"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("verifier/", views.verifier, name="verifier"),
    path("bn/installer/", views_bn.installer, name="bn_installer"),
    path("bn/fonctions/", views_bn.fonctions, name="bn_fonctions"),
    path("bn/echeances/", views_bn.echeances, name="bn_echeances"),
    path("bn/bureaux/", views_bn.bureaux_en_place, name="bn_bureaux"),
    path("bn/bureaux/<str:cle>/", views_bn.bureau_en_place, name="bn_bureau"),
    path("bn/bureaux/<str:cle>/remplacer/<int:pk>/", views_bn.remplacer, name="bn_remplacer"),
    path("bn/bureaux/<str:cle>/pourvoir/", views_bn.pourvoir, name="bn_pourvoir"),
    path("bn/validations/", views_bn.validations, name="bn_validations"),
    path(
        "bn/validations/<int:pk>/<str:decision>/",
        views_bn.decider_validation,
        name="bn_decider_validation",
    ),
    path("bn/delegations/", views_bn.delegations, name="bn_delegations"),
    path("bn/mandats-a-corriger/", views_bn.mandats_a_corriger, name="bn_mandats_a_corriger"),
    path(
        "bn/mandats-a-corriger/<int:pk>/fermer/",
        views_bn.fermer_mandat_incoherent,
        name="bn_fermer_mandat",
    ),
    path("<str:cle>/membres/", views.membres, name="membres"),
    path("<str:cle>/membres/<str:matricule>/", views.fiche_membre, name="fiche_membre"),
    path("<str:cle>/anciens/", views.anciens, name="anciens"),
    path(
        "<str:cle>/membres/<str:matricule>/reinitialiser/",
        views.reinitialiser,
        name="reinitialiser",
    ),
]
