from django.urls import path

from apps.courrier import views

app_name = "courrier"
urlpatterns = [
    path("a-signer/", views.a_signer, name="a_signer"),
    path("moi/", views.moi, name="moi"),
    path("ma-signature/", views.ma_signature, name="ma_signature"),
    path("ma-signature/image.png", views.ma_signature_image, name="ma_signature_image"),
    path("verifier/<str:jeton>/", views.verifier, name="verifier"),
    path("bn/registre/", views.bn_registre, name="bn_registre"),
    path("bn/clavier/", views.bn_clavier, name="bn_clavier"),
    path("c/<int:pk>/", views.detail, name="detail"),
    path("c/<int:pk>/action/", views.action, name="action"),
    path("c/<int:pk>/modifier/", views.modifier, name="modifier"),
    path("c/<int:pk>.pdf", views.pdf, name="pdf"),
    path("c/<int:pk>/original/", views.original, name="original"),
    path("c/<int:pk>/piece/<int:piece_pk>/", views.piece, name="piece"),
    path("<str:cle>/recus/", views.recus, name="recus"),
    path("<str:cle>/envoyes/", views.envoyes, name="envoyes"),
    path("<str:cle>/nouveau/", views.nouveau, name="nouveau"),
    path("<str:cle>/recherche/", views.recherche, name="recherche"),
]
