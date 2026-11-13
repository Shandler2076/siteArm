from django.urls import path

from apps.grades import views

app_name = "grades"
urlpatterns = [
    path("bn/serie/", views.bn_serie, name="bn_serie"),
    path("bn/eligibles/", views.bn_eligibles, name="bn_eligibles"),
    path("bn/sessions/", views.bn_sessions, name="bn_sessions"),
    path("bn/sessions/<int:pk>/", views.bn_session, name="bn_session"),
    path("bn/speciales/", views.bn_speciales, name="bn_speciales"),
    path("bn/actes/", views.bn_actes, name="bn_actes"),
    path("bn/actes/<int:pk>.pdf", views.acte_pdf_vue, name="acte_pdf"),
    path("bn/recherche/", views.recherche, name="recherche"),
    path("acte/<int:pk>/extrait.pdf", views.extrait_pdf, name="extrait"),
    path("bn/<str:matricule>/promouvoir/", views.bn_promouvoir, name="bn_promouvoir"),
    path("bn/<str:matricule>/corriger/", views.bn_corriger, name="bn_corriger"),
]
