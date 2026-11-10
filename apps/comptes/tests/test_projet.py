from django.conf import settings


def test_reglages_langue_et_fuseau():
    assert settings.LANGUAGE_CODE == "fr"
    assert settings.TIME_ZONE == "Africa/Porto-Novo"
    assert settings.USE_TZ is True
    assert settings.AUTH_USER_MODEL == "comptes.Compte"
