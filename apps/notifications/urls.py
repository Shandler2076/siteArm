from django.urls import path

from apps.notifications import views

app_name = "notifications"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("tout-lu/", views.tout_lu, name="tout_lu"),
    path("<int:pk>/", views.ouvrir, name="ouvrir"),
]
