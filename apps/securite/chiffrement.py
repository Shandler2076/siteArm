"""Chiffrement des clés de double vérification (Fernet : AES + contrôle d'intégrité).

Clé : DJANGO_CLE_DOUBLE_VERIFICATION si elle est fournie, sinon dérivée de la clé secrète du
site. Une copie de la base (pg_dump, dumpdata, fuite) ne donne donc plus les clés : il faut aussi
le fichier .env. Si la clé change, les clés deviennent illisibles : les titulaires refont leur
double vérification (commande reinitialiser_double_verification)."""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

PREFIXE = "chiffre:"
journal = logging.getLogger(__name__)


def _fernet() -> Fernet:
    source = getattr(settings, "CLE_DOUBLE_VERIFICATION", "") or settings.SECRET_KEY
    cle = hashlib.sha256(("double-verification:" + source).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(cle))


def chiffrer(valeur: str) -> str:
    if not valeur or valeur.startswith(PREFIXE):
        return valeur
    return PREFIXE + _fernet().encrypt(valeur.encode()).decode()


def dechiffrer(valeur: str) -> str:
    if not valeur or not valeur.startswith(PREFIXE):
        return valeur or ""  # ancienne clé en clair (avant chiffrement) : encore lisible
    try:
        return _fernet().decrypt(valeur[len(PREFIXE) :].encode()).decode()
    except InvalidToken:
        journal.error("Clé de double vérification illisible (clé de chiffrement changée ?)")
        return ""


class SecretChiffre(models.TextField):
    """En Python : la clé en clair ; en base et dans dumpdata : chiffrée."""

    def from_db_value(self, value, expression, connection):
        return dechiffrer(value)

    def to_python(self, value):
        return dechiffrer(value) if isinstance(value, str) else value

    def get_prep_value(self, value):
        return chiffrer(super().get_prep_value(value) or "")

    def value_to_string(self, obj):
        return chiffrer(self.value_from_object(obj) or "")


def chiffrer_les_cles_existantes(modele) -> None:
    for dv in modele.objects.exclude(secret=""):
        modele.objects.filter(pk=dv.pk).update(secret=dv.secret)
