"""Codes à 6 chiffres des applications d'authentification (TOTP, RFC 6238, SHA-1, 30 s)."""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote, urlencode

PERIODE = 30
CHIFFRES = 6
EMETTEUR = "Armée du Salut Bénin"


def nouveau_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode()


def _cle(secret: str) -> bytes:
    secret = secret.strip().replace(" ", "").upper()
    return base64.b32decode(secret + "=" * (-len(secret) % 8))


def code_pour_pas(secret: str, pas: int) -> str:
    empreinte = hmac.new(_cle(secret), struct.pack(">Q", pas), hashlib.sha1).digest()
    decalage = empreinte[-1] & 0x0F
    valeur = struct.unpack(">I", empreinte[decalage : decalage + 4])[0] & 0x7FFFFFFF
    return str(valeur % 10**CHIFFRES).zfill(CHIFFRES)


def code_totp(secret: str, instant: float) -> str:
    return code_pour_pas(secret, int(instant // PERIODE))


def verifier(secret: str, code: str, instant: float, dernier_pas: int | None) -> int | None:
    """Renvoie le pas accepté (fenêtre ±1), ou None. Un pas déjà utilisé est refusé."""
    code = "".join((code or "").split())
    if len(code) != CHIFFRES or not code.isdigit():
        return None
    courant = int(instant // PERIODE)
    for pas in (courant - 1, courant, courant + 1):
        if dernier_pas is not None and pas <= dernier_pas:
            continue
        if hmac.compare_digest(code_pour_pas(secret, pas), code):
            return pas
    return None


def uri_provisioning(secret: str, identifiant: str) -> str:
    etiquette = quote(f"{EMETTEUR}:{identifiant}")
    return f"otpauth://totp/{etiquette}?" + urlencode(
        {"secret": secret, "issuer": EMETTEUR, "digits": CHIFFRES, "period": PERIODE}
    )
