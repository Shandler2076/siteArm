from django.urls import path

from apps.securite import views

app_name = "securite"

urlpatterns = [
    path("activer/", views.activer, name="activer"),
    path("code/", views.code, name="code"),
]
