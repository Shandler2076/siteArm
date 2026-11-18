"""Courrier et communiqués (cahier des charges, module 4 ; décisions du 13 au 16/11/2026).

Seul `apps/courrier/services.py` écrit dans ces tables. Un courrier envoyé ne se supprime pas et
ne se modifie plus : il est enregistré au registre de son bureau.
"""

import secrets

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q

from apps.membres.stockage import stockage_prive


def _compte(nom, related_name="+"):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=related_name,
        verbose_name=nom,
    )


def _jeton() -> str:
    return secrets.token_urlsafe(24)


class Nature(models.TextChoices):
    LETTRE = "lettre", "Courrier"
    COMMUNIQUE = "communique", "Communiqué"


class Mode(models.TextChoices):
    REDIGE = "redige", "Rédigé sur le site"
    IMPORTE = "importe", "Courrier importé (photo, scan ou PDF)"


class Etat(models.TextChoices):
    A_SIGNER = "a_signer", "En attente de signature"
    A_CORRIGER = "a_corriger", "En correction"
    ENVOYE = "envoye", "Envoyé"
    ANNULE = "annule", "Abandonné"


class Langue(models.TextChoices):
    FRANCAIS = "fr", "Français"
    GOUN = "gun", "Goun"


class Police(models.TextChoices):
    """Polices du courrier (décision du 18/11/2026) ; fichiers dans static/fonts/courrier/."""

    LIBERATION_SERIF = "liberation_serif", "Liberation Serif (type Times New Roman)"
    LIBERATION_SANS = "liberation_sans", "Liberation Sans (type Arial)"
    CHARIS = "charis", "Charis SIL (langues africaines, Bibles)"
    GENTIUM = "gentium", "Gentium Plus"
    NOTO_SERIF = "noto_serif", "Noto Serif"


POLICE_PAR_LANGUE = {Langue.FRANCAIS: Police.LIBERATION_SERIF, Langue.GOUN: Police.CHARIS}
TAILLES = (10, 11, 12, 13)
TAILLE_MIN_UNE_PAGE = 9


class Qualite(models.TextChoices):
    TITULAIRE = "titulaire", "Signé par le titulaire"
    PO = "po", "Signé pour ordre (P.O.)"


class SignatureDeposee(models.Model):
    """Image de la signature d'un signataire, déposée par lui-même dans son compte.

    Elle ne sert qu'aux courriers que ce compte valide lui-même. Une signature remplacée reste
    enregistrée (inactive) : les courriers déjà signés la gardent.
    """

    compte = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="signatures"
    )
    image = models.ImageField("image", storage=stockage_prive, upload_to="signatures/")
    active = models.BooleanField("active", default=True)
    deposee_le = models.DateTimeField("déposée le", auto_now_add=True)

    class Meta:
        verbose_name = "signature déposée"
        ordering = ["-deposee_le"]
        constraints = [
            models.UniqueConstraint(
                fields=["compte"], condition=Q(active=True), name="une_signature_active"
            )
        ]

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Une signature déposée ne se supprime pas : elle se remplace.")


class Courrier(models.Model):
    nature = models.CharField("nature", max_length=12, choices=Nature.choices)
    mode = models.CharField("façon", max_length=10, choices=Mode.choices, default=Mode.REDIGE)
    expediteur_cle = models.CharField("bureau expéditeur", max_length=30)
    expediteur_libelle = models.CharField("bureau expéditeur (libellé)", max_length=200)
    annee = models.PositiveSmallIntegerField("année")
    numero_ordre = models.PositiveIntegerField("numéro d'ordre")
    numero = models.CharField("numéro complet", max_length=120, blank=True)
    lieu = models.CharField("lieu", max_length=100)
    langue = models.CharField(
        "langue", max_length=3, choices=Langue.choices, default=Langue.FRANCAIS
    )
    adresse = models.TextField("ligne d'adresse", blank=True)
    police = models.CharField(
        "police", max_length=20, choices=Police.choices, default=Police.LIBERATION_SERIF
    )
    taille = models.PositiveSmallIntegerField("taille du texte", default=12)
    une_page = models.BooleanField("tenir sur une page", default=False)
    objet = models.CharField("objet", max_length=250)
    texte = models.TextField("texte", blank=True)
    fichier = models.FileField(
        "courrier importé", storage=stockage_prive, upload_to="courrier/", blank=True
    )
    etat = models.CharField("état", max_length=12, choices=Etat.choices, default=Etat.A_SIGNER)
    motif_renvoi = models.CharField("motif du renvoi", max_length=300, blank=True)
    prepare_par = _compte("préparé par")
    date_preparation = models.DateTimeField("préparé le", auto_now_add=True)
    signe_par = _compte("signé par")
    qualite = models.CharField("qualité", max_length=10, choices=Qualite.choices, blank=True)
    fonction_signataire = models.CharField("fonction du signataire", max_length=150, blank=True)
    nom_signataire = models.CharField("nom du signataire", max_length=250, blank=True)
    signature = models.ForeignKey(
        SignatureDeposee, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    date_envoi = models.DateTimeField("envoyé le", null=True, blank=True)
    date_abandon = models.DateTimeField("abandonné le", null=True, blank=True)
    version = models.PositiveIntegerField("version", default=1)
    jeton = models.CharField("jeton de vérification", max_length=64, unique=True, default=_jeton)

    class Meta:
        verbose_name = "courrier"
        ordering = ["-date_preparation"]
        constraints = [
            models.UniqueConstraint(
                fields=["expediteur_cle", "annee", "numero_ordre"],
                condition=Q(etat="envoye"),
                name="numero_ordre_unique_par_bureau_et_annee",
            )
        ]

    def __str__(self) -> str:
        return f"{self.numero or f'{self.numero_ordre:03d} (non envoyé)'} — {self.objet}"

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Un courrier ne se supprime pas.")

    @property
    def envoye(self) -> bool:
        return self.etat == Etat.ENVOYE

    @property
    def communique(self) -> bool:
        return self.nature == Nature.COMMUNIQUE


class TypeDestinataire(models.TextChoices):
    BUREAU = "bureau", "Bureau"
    MEMBRE = "membre", "Membre"


class Destinataire(models.Model):
    """Un bureau (reçu par son responsable) ou un membre à qui le courrier est adressé."""

    courrier = models.ForeignKey(Courrier, on_delete=models.PROTECT, related_name="destinataires")
    type = models.CharField("type", max_length=8, choices=TypeDestinataire.choices)
    unite_cle = models.CharField("bureau", max_length=30, blank=True)
    libelle = models.CharField("libellé", max_length=250)
    membre = models.ForeignKey(
        "membres.Membre", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    transmis_par = models.CharField(
        "transmis par le bureau", max_length=30, blank=True
    )  # communiqué transmis aux membres par leur paroisse
    recu_le = models.DateTimeField("reçu le", null=True, blank=True)
    lu_le = models.DateTimeField("ouvert le", null=True, blank=True)
    lu_par = _compte("ouvert par")
    accuse_le = models.DateTimeField("« Courrier reçu » le", null=True, blank=True)
    accuse_par = _compte("« Courrier reçu » par")

    class Meta:
        verbose_name = "destinataire"
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["courrier", "unite_cle"],
                condition=Q(type="bureau"),
                name="bureau_destinataire_unique",
            ),
            models.UniqueConstraint(
                fields=["courrier", "membre"],
                condition=Q(type="membre"),
                name="membre_destinataire_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.libelle

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Un destinataire ne se supprime pas.")


class PieceJointe(models.Model):
    courrier = models.ForeignKey(Courrier, on_delete=models.PROTECT, related_name="pieces")
    fichier = models.FileField("fichier", storage=stockage_prive, upload_to="courrier/pieces/")
    nom = models.CharField("nom", max_length=200)

    class Meta:
        verbose_name = "pièce jointe"
        ordering = ["pk"]

    def __str__(self) -> str:
        return self.nom


# --- Clavier goun --------------------------------------------------------------------------------
# Liste du mainteneur (18/11/2026, d'après le gun de la Bible de 1923) : lettres à point souscrit,
# puis les tons, qui se posent sur la lettre déjà tapée (« ◌ » marque une touche de ton).
LETTRES_PAR_DEFAUT = "ẹ ọ ṣ \u25cc\u0301 \u25cc\u0300 \u25cc\u0303 \u25cc\u0302"


class ReglagesClavier(models.Model):
    """Lettres et tons du clavier goun (liste réglable par le Bureau national)."""

    lettres = models.TextField("lettres du clavier", default=LETTRES_PAR_DEFAUT)

    class Meta:
        verbose_name = "réglages du clavier goun"

    @classmethod
    def courant(cls) -> "ReglagesClavier":
        return cls.objects.order_by("pk").first() or cls.objects.create()

    def liste(self) -> list[str]:
        vues, resultat = set(), []
        for lettre in self.lettres.split():
            if lettre not in vues:
                vues.add(lettre)
                resultat.append(lettre)
        return resultat


class OrigineMot(models.TextChoices):
    BN = "bn", "Liste du Bureau national"
    APPRIS = "appris", "Appris des courriers"
    LEXIQUE = "lexique", "Lexique goun (Bible de 1923)"


def cle_de_recherche(mot: str) -> str:
    """Mot sans points ni tons, en minuscules : « sọ́ » → « so »."""
    import unicodedata

    decompose = unicodedata.normalize("NFD", mot or "").lower()
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


class MotClavier(models.Model):
    """Mot proposé par le clavier : liste du BN, lexique goun, ou appris des courriers envoyés."""

    mot = models.CharField("mot", max_length=60, unique=True)
    cle = models.CharField("clé de recherche", max_length=60, db_index=True, editable=False)
    origine = models.CharField("origine", max_length=8, choices=OrigineMot.choices)
    nombre = models.PositiveIntegerField("nombre d'emplois", default=0)
    actif = models.BooleanField("proposé", default=True)

    class Meta:
        verbose_name = "mot du clavier"
        verbose_name_plural = "mots du clavier"
        ordering = ["-nombre", "mot"]

    def __str__(self) -> str:
        return self.mot

    def save(self, *args, **kwargs):
        self.cle = cle_de_recherche(self.mot)[:60]
        super().save(*args, **kwargs)
