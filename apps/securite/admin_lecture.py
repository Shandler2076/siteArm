"""Gestion technique (/gestion/) en lecture seule sur le vrai site (ADMIN_LECTURE_SEULE).

La gestion écrit directement en base, sans passer par les services (journal, revérifications) :
sur le vrai site, on peut seulement y consulter. Les actions « Fermer » / « Rouvrir » une unité
restent permises. Pour une opération exceptionnelle (autorisation de transition…), le mainteneur
met DJANGO_ADMIN_LECTURE_SEULE=False dans .env, redémarre, fait l'opération, puis remet True.
"""

from django.conf import settings
from django.contrib import admin


def _lecture_seule() -> bool:
    return bool(getattr(settings, "ADMIN_LECTURE_SEULE", False))


def _garde(methode):
    def verifiee(request, *args, **kwargs):
        if _lecture_seule():
            return False
        return methode(request, *args, **kwargs)

    return verifiee


def _vue(model_admin):
    origine_vue = model_admin.has_view_permission
    origine_modif = model_admin.__class__.has_change_permission

    def vue(request, obj=None):
        # Consulter reste permis même quand « modifier » est refusé.
        if _lecture_seule():
            return origine_vue(request, obj) or origine_modif(model_admin, request, obj)
        return origine_vue(request, obj)

    return vue


def mettre_la_gestion_en_lecture_seule() -> None:
    for model_admin in admin.site._registry.values():
        model_admin.has_view_permission = _vue(model_admin)
        for nom in ("has_add_permission", "has_change_permission", "has_delete_permission"):
            setattr(model_admin, nom, _garde(getattr(model_admin, nom)))
