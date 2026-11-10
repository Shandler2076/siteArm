from django.urls import path

from apps.listes import views

app_name = "listes"

urlpatterns = [
    path("<str:cle>/listes/", views.liste, name="liste"),
    path("<str:cle>/listes/pdf/", views.liste_pdf_vue, name="liste_pdf"),
    path("<str:cle>/listes/excel/", views.liste_excel_vue, name="liste_excel"),
    path("<str:cle>/statistiques/", views.statistiques, name="statistiques"),
    path("<str:cle>/statistiques/pdf/", views.statistiques_pdf_vue, name="statistiques_pdf"),
]
