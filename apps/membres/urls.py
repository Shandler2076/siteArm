from django.urls import path

from apps.membres import views_bn, views_fichiers, views_membre

app_name = "membres"

urlpatterns = [
    path("ma-fiche/", views_membre.ma_fiche, name="ma_fiche"),
    path("ma-fiche/coordonnees/", views_membre.mes_coordonnees, name="mes_coordonnees"),
    path("ma-fiche/fiche.pdf", views_membre.ma_fiche_pdf, name="ma_fiche_pdf"),
    path("ma-fiche/photo/", views_membre.ma_photo, name="ma_photo"),
    path("photos/<int:pk>/", views_fichiers.photo, name="photo"),
    path("<str:matricule>/cip/", views_fichiers.cip, name="cip"),
    path("bn/enregistrer/", views_bn.enregistrer, name="bn_enregistrer"),
    path("bn/photos/", views_bn.photos, name="bn_photos"),
    path("bn/<str:matricule>/", views_bn.fiche, name="bn_fiche"),
    path("bn/<str:matricule>/fiche.pdf", views_bn.fiche_pdf, name="bn_fiche_pdf"),
    path(
        "bn/<str:matricule>/fiche-identifiants.pdf",
        views_bn.fiche_identifiants_pdf,
        name="bn_fiche_identifiants",
    ),
]
