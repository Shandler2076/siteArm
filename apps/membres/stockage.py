"""Stockage privé : fichiers sensibles (photos, CIP) jamais servis par une URL publique."""

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class StockagePrive(FileSystemStorage):
    def __init__(self):
        super().__init__(base_url=None)

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        import os

        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Les fichiers privés n'ont pas d'adresse publique.")


stockage_prive = StockagePrive()
