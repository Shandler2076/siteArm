from django.urls import path

from apps.evenements import views

app_name = "evenements"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.nouveau, name="nouveau"),
    path("moi/", views.mes_evenements, name="moi"),
    path("autorisation/<int:pk>.pdf", views.autorisation, name="autorisation"),
    path("verifier/<str:jeton>/", views.verifier, name="verifier"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/modifier/", views.modifier, name="modifier"),
    path("<int:pk>/convoquer/", views.convoquer_vue, name="convoquer"),
    path("<int:pk>/recherche-membres/", views.recherche_membres, name="recherche_membres"),
    path("<int:pk>/pointage/", views.pointage, name="pointage"),
    path("<int:pk>/convoques.xlsx", views.export_excel, name="export_excel"),
    path("<int:pk>/convoques.pdf", views.export_pdf, name="export_pdf"),
    path("<int:pk>/autorisations.pdf", views.autorisations_pdf, name="autorisations"),
]
