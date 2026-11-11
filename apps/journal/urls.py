from django.urls import path

from apps.journal import views

app_name = "journal"

urlpatterns = [path("", views.liste, name="liste")]
