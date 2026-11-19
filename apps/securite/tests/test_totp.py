import base64

from apps.securite.totp import code_totp, nouveau_secret, uri_provisioning, verifier

SECRET_RFC = base64.b32encode(b"12345678901234567890").decode()


def test_vecteur_rfc6238():
    assert code_totp(SECRET_RFC, 59) == "287082"
    assert code_totp(SECRET_RFC, 1111111109) == "081804"


def test_fenetre_et_rejeu():
    pas = verifier(SECRET_RFC, "287082", 59, None)
    assert pas == 1
    assert verifier(SECRET_RFC, "287082", 59 + 30, None) == 1  # pas précédent toléré
    assert verifier(SECRET_RFC, "287082", 59, dernier_pas=1) is None  # déjà utilisé
    assert verifier(SECRET_RFC, "000000", 59, None) is None
    assert verifier(SECRET_RFC, "abc", 59, None) is None
    assert verifier(SECRET_RFC, " 287 082 ", 59, None) == 1


def test_nouveau_secret_et_uri():
    s = nouveau_secret()
    assert len(base64.b32decode(s)) == 20
    uri = uri_provisioning(s, "2015-01AS-0001")
    assert uri.startswith("otpauth://totp/") and f"secret={s}" in uri and "issuer=" in uri


def test_uri_courte_et_lisible_par_google_authenticator():
    """Code QR : contenu ASCII, espaces en %20 (jamais « + »), sans réglages par défaut."""
    uri = uri_provisioning("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", "2015-01AS-0001")
    assert uri.isascii() and "+" not in uri and "%C3" not in uri
    assert uri.startswith("otpauth://totp/Armee%20du%20Salut%20Benin:2015-01AS-0001?")
    assert "issuer=Armee%20du%20Salut%20Benin" in uri
    assert "digits=" not in uri and "period=" not in uri
