"""Contrôle et préparation des photos d'identité déposées par les membres."""

import io
import warnings

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

TAILLE_MAX = 5 * 1024 * 1024
COTE_MIN = 300
COTE_MAX_STOCKE = 800
FORMATS = {"JPEG", "PNG"}


class PhotoInvalide(ValueError):
    pass


def verifier_et_preparer_photo(fichier) -> ContentFile:
    """Refuse ce qui n'est pas une vraie photo JPEG/PNG correcte ; renvoie un JPEG nettoyé."""
    if fichier.size > TAILLE_MAX:
        raise PhotoInvalide("La photo dépasse 5 Mo.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            fichier.seek(0)
            Image.open(fichier).verify()
            fichier.seek(0)
            image = Image.open(fichier)
            image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise PhotoInvalide("La photo est trop grande (dimensions démesurées).") from e
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise PhotoInvalide("Format refusé : envoyez une photo JPEG ou PNG.") from e
    if image.format not in FORMATS:
        raise PhotoInvalide("Format refusé : envoyez une photo JPEG ou PNG.")
    if min(image.size) < COTE_MIN:
        raise PhotoInvalide("La photo est trop petite (300 × 300 pixels minimum).")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((COTE_MAX_STOCKE, COTE_MAX_STOCKE))
    sortie = io.BytesIO()
    image.save(sortie, "JPEG", quality=85)  # sans métadonnées (exif non recopié)
    return ContentFile(sortie.getvalue(), name="photo.jpg")


MESSAGE_CIP = (
    "Format refusé : la photo du CIP doit être un fichier JPEG, PNG ou PDF (5 Mo au plus)."
)


def type_piece_cip(fichier) -> str:
    """Renvoie l'extension (jpg, png, pdf) d'une pièce CIP valide, sinon lève PhotoInvalide."""
    if fichier.size > TAILLE_MAX:
        raise PhotoInvalide(MESSAGE_CIP)
    fichier.seek(0)
    debut = fichier.read(5)
    fichier.seek(0)
    if debut.startswith(b"%PDF"):
        return "pdf"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(fichier)
            image.verify()
    except Exception as e:  # noqa: BLE001 — tout fichier illisible est refusé
        raise PhotoInvalide(MESSAGE_CIP) from e
    finally:
        fichier.seek(0)
    formats = {"JPEG": "jpg", "PNG": "png"}
    if image.format not in formats:
        raise PhotoInvalide(MESSAGE_CIP)
    return formats[image.format]
