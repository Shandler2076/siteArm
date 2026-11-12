from django.urls import path

from apps.grades import views

app_name = "grades"
urlpatterns = [
    path("bn/serie/", views.bn_serie, name="bn_serie"),
    path("bn/<str:matricule>/promouvoir/", views.bn_promouvoir, name="bn_promouvoir"),
    path("bn/<str:matricule>/corriger/", views.bn_corriger, name="bn_corriger"),
]
