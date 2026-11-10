from django.urls import path

from apps.membres import views_bn

app_name = "membres"

urlpatterns = [
    path("bn/enregistrer/", views_bn.enregistrer, name="bn_enregistrer"),
    path("bn/<str:matricule>/", views_bn.fiche, name="bn_fiche"),
    path("bn/<str:matricule>/fiche.pdf", views_bn.fiche_pdf, name="bn_fiche_pdf"),
    path(
        "bn/<str:matricule>/fiche-identifiants.pdf",
        views_bn.fiche_identifiants_pdf,
        name="bn_fiche_identifiants",
    ),
]
