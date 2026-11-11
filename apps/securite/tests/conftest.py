import pytest

from apps.bureaux.tests.conftest import (  # noqa: F401
    client_technique,
    compte_technique,
    donner_mandat,
    monde,
    nouveau_membre,
    territoire,
)


@pytest.fixture(autouse=True)
def _avec_double_verification(_sans_double_verification, settings):
    settings.DOUBLE_VERIFICATION_BN = True
