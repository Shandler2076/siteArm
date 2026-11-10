from django.urls import path

from apps.lots import views

app_name = "lots"

urlpatterns = [
    path("modele/<str:code>.xlsx", views.modele, name="modele"),
]
