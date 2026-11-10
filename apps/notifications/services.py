import logging
from collections.abc import Iterable

from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.models import Notification

SUJET = "Armée du Salut — notification"
journal = logging.getLogger(__name__)


def notifier(comptes: Iterable, message: str, lien: str = "") -> int:
    """Une notification par compte actif distinct, et un email si le membre en a un."""
    vus, creees = set(), 0
    for compte in comptes:
        if compte is None or compte.pk in vus or not compte.is_active:
            continue
        vus.add(compte.pk)
        Notification.objects.create(destinataire=compte, message=message[:300], lien=lien)
        creees += 1
        email = getattr(getattr(compte, "membre", None), "email", "")
        if email:
            corps = message + (f"\n\n{settings.SITE_URL.rstrip('/')}{lien}" if lien else "")
            try:
                send_mail(SUJET, corps, None, [email])
            except Exception:  # noqa: BLE001 — un email raté ne doit jamais bloquer le site
                journal.exception("Échec de l'envoi de l'email de notification à %s", email)
    return creees


def notifier_unite(unite, message: str, lien: str = "") -> int:
    from apps.bureaux.perimetre import titulaires_gestion

    return notifier(titulaires_gestion(unite), message, lien)
