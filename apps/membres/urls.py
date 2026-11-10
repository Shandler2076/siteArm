from django.urls import path

from apps.membres import views_bn

app_name = "membres"

urlpatterns = [
    path("bn/enregistrer/", views_bn.enregistrer, name="bn_enregistrer"),
    path("bn/<str:matricule>/", views_bn.fiche, name="bn_fiche"),
]
