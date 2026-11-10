"""Réglages du site. Les valeurs sensibles viennent des variables d'environnement."""

import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(nom: str, defaut: bool = False) -> bool:
    return os.environ.get(nom, str(defaut)).strip().lower() in {"1", "true", "vrai", "oui"}


def _liste(nom: str) -> list[str]:
    return [v.strip() for v in os.environ.get(nom, "").split(",") if v.strip()]


DEBUG = _bool("DJANGO_DEBUG", False)
EN_TEST = "pytest" in sys.modules

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or EN_TEST:
        SECRET_KEY = "cle-de-developpement-non-secrete"
    else:
        raise ImproperlyConfigured("La variable DJANGO_SECRET_KEY est obligatoire en production.")

ALLOWED_HOSTS = _liste("DJANGO_ALLOWED_HOSTS") or (["localhost", "127.0.0.1"] if DEBUG else [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.comptes",
    "apps.organisation",
    "apps.membres",
    "axes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.comptes.middleware.ChangementMotDePasseObligatoire",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600
    )
}

AUTH_USER_MODEL = "comptes.Compte"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.comptes.backends.IdentifiantNormaliseBackend",
]

# Blocage après 5 échecs, pendant 15 minutes, par identifiant.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_USERNAME_FORM_FIELD = "username"
AXES_USERNAME_CALLABLE = "apps.comptes.securite.identifiant_pour_blocage"
AXES_LOCKOUT_TEMPLATE = "comptes/compte_bloque.html"
AXES_HTTP_RESPONSE_CODE = 429
AXES_RESET_ON_SUCCESS = True
# Blocage volontairement par identifiant seul : bloquer par adresse IP bloquerait tous les
# membres d'un même cybercafé ou d'un même réseau mobile après 5 échecs cumulés.
SILENCED_SYSTEM_CHECKS = [
    "axes.W006",
    # Pas d'inscription à la liste HSTS « preload » : engagement difficile à annuler.
    "security.W021",
]

# Session : déconnexion après 2 h d'inactivité.
SESSION_COOKIE_AGE = 7200
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.comptes.validators.DifferentDeLIdentifiantValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Fichiers privés (photos, CIP) : jamais servis directement, seulement via des vues contrôlées.
PRIVATE_MEDIA_ROOT = BASE_DIR / "prive"

# Adresse publique du site (imprimée sur les fiches d'identification).
SITE_URL = os.environ.get("DJANGO_SITE_URL", "http://127.0.0.1:8000")
WHITENOISE_USE_FINDERS = DEBUG or EN_TEST
WHITENOISE_AUTOREFRESH = DEBUG or EN_TEST
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or EN_TEST
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

LOGIN_URL = "connexion"
LOGIN_REDIRECT_URL = "accueil"
LOGOUT_REDIRECT_URL = "connexion"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sécurité HTTPS en production (l'hébergeur termine le HTTPS devant le site).
CSRF_TRUSTED_ORIGINS = _liste("DJANGO_CSRF_TRUSTED_ORIGINS")
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
if not DEBUG:
    SECURE_SSL_REDIRECT = not EN_TEST
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
