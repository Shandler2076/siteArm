from django.urls import path

from apps.tresorerie import views

app_name = "tresorerie"
urlpatterns = [
    path("payer/", views.payer, name="payer"),
    path("payer-pour/", views.payer_pour, name="payer_pour"),
    path("speciale/<int:pk>/payer/", views.payer_speciale, name="payer_speciale"),
    path("paiement/<str:reference>/", views.paiement, name="paiement"),
    path("quittance/<int:pk>.pdf", views.quittance, name="quittance"),
    path("bn/speciales/", views.bn_speciales, name="bn_speciales"),
    path("bn/speciales/<int:pk>/", views.bn_speciale, name="bn_speciale"),
    path("bn/numeros/", views.bn_numeros, name="bn_numeros"),
    path("bn/reversements/", views.bn_reversements, name="bn_reversements"),
    path("<str:cle>/", views.espace, name="espace"),
    path("<str:cle>/payer-membres/", views.payer_membres, name="payer_membres"),
]
