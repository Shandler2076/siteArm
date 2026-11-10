import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.bureaux.tests.conftest import (  # noqa: F401
    client_technique,
    compte_technique,
    donner_mandat,
    nouveau_membre,
    territoire,
)


@pytest.fixture
def classeur():
    from openpyxl import Workbook

    from apps.lots.colonnes import COLONNES

    def fabriquer(lignes, entetes_modifiees=None, nom="lot.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "Membres"
        entetes = [c.entete for c in COLONNES]
        for i, e in (entetes_modifiees or {}).items():
            entetes[i] = e
        ws.append(entetes)
        for ligne in lignes:
            ws.append(list(ligne))
        tampon = io.BytesIO()
        wb.save(tampon)
        return SimpleUploadedFile(nom, tampon.getvalue())

    return fabriquer
