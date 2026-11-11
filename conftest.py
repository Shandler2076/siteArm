import pytest


@pytest.fixture(autouse=True)
def _sans_double_verification(settings):
    """La double vérification BN est testée dans apps/securite ; ailleurs elle gênerait."""
    settings.DOUBLE_VERIFICATION_BN = False
