from django.urls import path

from apps.bureaux import views_bn

app_name = "bureaux"

urlpatterns = [
    path("bn/installer/", views_bn.installer, name="bn_installer"),
    path("bn/fonctions/", views_bn.fonctions, name="bn_fonctions"),
]
