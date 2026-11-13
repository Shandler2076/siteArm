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


def lien_membre(membre) -> str:
    """Lien symbolique vers un membre : chacun arrive sur la page qu'il a le droit de voir."""
    return f"membre:{membre.matricule}"


def resoudre_lien(compte, lien: str) -> str | None:
    """Adresse où mène une notification pour ce compte, ou None (simple information).

    - « membre:<matricule> » : sa propre fiche, la fiche BN, ou la fiche dans l'espace d'un bureau
      dont le périmètre contient ce membre (le gardien des périmètres décide) ;
    - une adresse interne (« /… ») est gardée telle quelle ; jamais d'adresse externe.
    """
    lien = (lien or "").strip()
    if lien.startswith("membre:"):
        from apps.bureaux.perimetre import membres_visibles, unites_gerees
        from apps.membres.models import Membre

        matricule = lien.removeprefix("membre:")
        membre = Membre.objects.filter(matricule=matricule).first()
        if membre is None:
            return None
        if membre.compte_id and membre.compte_id == compte.pk:
            return "/membres/ma-fiche/"
        if compte.has_perm("membres.gerer_membres"):
            return f"/membres/bn/{matricule}/"
        for unite in unites_gerees(compte):
            if membres_visibles(unite).filter(pk=membre.pk).exists():
                return f"/bureau/{unite.cle}/membres/{matricule}/"
        return None
    if lien.startswith("/") and not lien.startswith("//"):
        return lien
    return None
