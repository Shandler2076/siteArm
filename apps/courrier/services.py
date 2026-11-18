"""Seuls points d'écriture du courrier et des communiqués (décisions du 13 au 16/11/2026).

Circuit d'un courrier : le Secrétaire (ou le Chef) prépare → le signataire (Président ou Chef ;
le Secrétaire « pour ordre ») valide avec son propre compte et SA signature déposée → le courrier
part : notification (et e-mail) au responsable de chaque bureau destinataire et aux membres
désignés. Un courrier envoyé ne se modifie plus.
"""

import io
import re
import unicodedata
import warnings

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import F, Max, Q
from django.utils import timezone
from PIL import Image, ImageChops, UnidentifiedImageError

from apps.bureaux.perimetre import (
    Niveau,
    Unite,
    membres_visibles,
    peut_deposer_signature,
    qualite_signataire,
    unite_par_cle,
    unites_courrier,
    unites_inferieures,
)
from apps.comptes.models import Compte
from apps.courrier.models import (
    Courrier,
    Destinataire,
    Etat,
    Mode,
    MotClavier,
    Nature,
    OrigineMot,
    PieceJointe,
    Qualite,
    ReglagesClavier,
    SignatureDeposee,
    TypeDestinataire,
)

TAILLE_MAX = 10 * 1024 * 1024
PIECES_MAX = 5
SORTIS = {"exclu", "demissionnaire", "decede"}
SIGLES = {Niveau.PAROISSE: "UP", Niveau.CIRCUIT: "SC", Niveau.REGION: "BRC"}
LIEU_NATIONAL = "Porto-Novo"
JETON = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class CourrierRefuse(Exception):
    """Opération refusée ; le message s'affiche tel quel."""


def _journal(par, action, unite="", **details):
    from apps.journal.services import journaliser

    journaliser(par, action, unite=unite, **details)


# --- Présentation du bureau expéditeur -----------------------------------------------------------
def _sans_accents(texte: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def _nom_propre(unite: Unite) -> str:
    """Nom de l'unité sans « Paroisse », « Circuit » ou « Région » en tête."""
    nom = unite.objet.nom.strip()
    for prefixe in ("paroisse ", "circuit ", "région ", "region "):
        if nom.lower().startswith(prefixe):
            return nom[len(prefixe) :].strip()
    return nom


def sigle_bureau(unite: Unite) -> str:
    if unite.niveau == Niveau.NATIONAL:
        return "BNC"
    nom = re.sub(r"[^A-Z0-9]+", "-", _sans_accents(_nom_propre(unite)).upper()).strip("-")
    return f"{SIGLES[unite.niveau]}-{nom}"


def numero_complet(unite: Unite, numero_ordre: int, annee: int) -> str:
    auteur = "SN" if unite.niveau == Niveau.NATIONAL else "S"
    return f"{numero_ordre:03d}-{annee}/CCOSECS-CNC/AS/{sigle_bureau(unite)}/{auteur}"


def ligne_bureau(unite: Unite) -> str:
    """Dernière ligne du bandeau d'en-tête."""
    if unite.niveau == Niveau.NATIONAL:
        return "BUREAU NATIONAL DE COMMANDEMENT"
    nom = _nom_propre(unite).upper()
    if unite.niveau == Niveau.PAROISSE:
        region = unite.objet.circuit.region.nom.upper()
        return f"UNITÉ PAROISSIALE DE {nom} — RÉGION {region}"
    if unite.niveau == Niveau.CIRCUIT:
        return f"SECTION CIRCUIT DE {nom} — RÉGION {unite.objet.region.nom.upper()}"
    return f"BUREAU RÉGIONAL DE COORDINATION — {nom}"


def nom_bureau(unite: Unite) -> str:
    """Nom du bureau sous le numéro d'ordre (« Bureau National de Commandement »…)."""
    if unite.niveau == Niveau.NATIONAL:
        return "Bureau National de Commandement"
    nom = _nom_propre(unite)
    return {
        Niveau.PAROISSE: f"Unité paroissiale de {nom}",
        Niveau.CIRCUIT: f"Section circuit de {nom}",
        Niveau.REGION: f"Bureau régional de coordination — {nom}",
    }[unite.niveau]


def lieu_par_defaut(unite: Unite) -> str:
    return LIEU_NATIONAL if unite.niveau == Niveau.NATIONAL else _nom_propre(unite)


def unite_expeditrice(courrier: Courrier) -> Unite | None:
    return unite_par_cle(courrier.expediteur_cle)


# --- Numéro d'ordre ------------------------------------------------------------------------------
def proposer_numero(unite: Unite, annee: int) -> int:
    dernier = Courrier.objects.filter(
        expediteur_cle=unite.cle, annee=annee, etat=Etat.ENVOYE
    ).aggregate(m=Max("numero_ordre"))["m"]
    en_cours = Courrier.objects.filter(
        expediteur_cle=unite.cle, annee=annee, etat__in=(Etat.A_SIGNER, Etat.A_CORRIGER)
    ).aggregate(m=Max("numero_ordre"))["m"]
    return max(dernier or 0, en_cours or 0) + 1


def _verifier_numero(unite: Unite, annee: int, numero_ordre: int, sauf=None) -> None:
    if not numero_ordre or numero_ordre < 1 or numero_ordre > 99999:
        raise CourrierRefuse("Le numéro d'ordre doit être un nombre positif.")
    deja = Courrier.objects.filter(
        expediteur_cle=unite.cle, annee=annee, numero_ordre=numero_ordre, etat=Etat.ENVOYE
    )
    if sauf is not None:
        deja = deja.exclude(pk=sauf.pk)
    if deja.exists():
        raise CourrierRefuse(
            f"Le numéro {numero_ordre:03d}-{annee} est déjà employé par un courrier envoyé de ce "
            f"bureau. Numéro proposé : {proposer_numero(unite, annee):03d}."
        )


# --- Fichiers ------------------------------------------------------------------------------------
MESSAGE_FORMAT = "Format refusé : envoyez un fichier PDF, JPEG ou PNG de 10 Mo au plus."


def type_fichier(fichier) -> str:
    """« pdf », « jpg » ou « png » ; sinon CourrierRefuse."""
    if fichier.size > TAILLE_MAX:
        raise CourrierRefuse(MESSAGE_FORMAT)
    fichier.seek(0)
    debut = fichier.read(5)
    fichier.seek(0)
    if debut.startswith(b"%PDF"):
        _verifier_pdf(fichier)
        return "pdf"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(fichier)
            image.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise CourrierRefuse("L'image est trop grande (dimensions démesurées).") from e
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise CourrierRefuse(MESSAGE_FORMAT) from e
    finally:
        fichier.seek(0)
    formats = {"JPEG": "jpg", "PNG": "png"}
    if image.format not in formats:
        raise CourrierRefuse(MESSAGE_FORMAT)
    return formats[image.format]


def _verifier_pdf(fichier) -> None:
    """Refuse un PDF illisible ou protégé : il ne pourrait pas être joint au courrier imprimé."""
    from pypdf import PdfReader

    try:
        lecteur = PdfReader(fichier)
        if lecteur.is_encrypted or len(lecteur.pages) < 1:
            raise CourrierRefuse("PDF protégé ou vide : enregistrez-le sans mot de passe.")
    except CourrierRefuse:
        raise
    except Exception as e:  # noqa: BLE001 — tout PDF mal formé est refusé ici, pas plus tard
        raise CourrierRefuse(
            "Ce PDF est illisible. Enregistrez-le de nouveau, ou scannez-le."
        ) from e
    finally:
        fichier.seek(0)


def _contenu_nettoye(fichier, extension: str):
    """Les images sont réenregistrées sans métadonnées (position GPS, appareil…)."""
    if extension == "pdf":
        return fichier
    from PIL import ImageOps

    fichier.seek(0)
    image = Image.open(fichier)
    image.load()
    image = ImageOps.exif_transpose(image)
    sortie = io.BytesIO()
    if extension == "jpg":
        image.convert("RGB").save(sortie, "JPEG", quality=88)
    else:
        image.save(sortie, "PNG")
    return ContentFile(sortie.getvalue())


def _nom_de_fichier(nom: str, extension: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", _sans_accents(nom.rsplit(".", 1)[0]))[:60].strip("-")
    return f"{base or 'fichier'}.{extension}"


# --- Destinataires -------------------------------------------------------------------------------
def _bureaux_permis(unite: Unite) -> dict[str, Unite]:
    """Bureaux auxquels ce bureau peut écrire : tous pour le BN ; le BN et les bureaux placés
    en dessous pour un bureau local."""
    permis = {u.cle: u for u in unites_inferieures(unite)}
    if unite.niveau != Niveau.NATIONAL:
        permis["national"] = Unite(Niveau.NATIONAL, None)
    return permis


def bureaux_proposes(unite: Unite) -> list[Unite]:
    return list(_bureaux_permis(unite).values())


def _destinataires(unite: Unite, bureaux, niveaux, membres) -> tuple[list[Unite], list]:
    permis = _bureaux_permis(unite)
    choisis: dict[str, Unite] = {}
    for cle in bureaux or []:
        if cle not in permis:
            raise CourrierRefuse("Un des bureaux choisis ne peut pas recevoir ce courrier.")
        choisis[cle] = permis[cle]
    for niveau in niveaux or []:
        if niveau not in (Niveau.REGION, Niveau.CIRCUIT, Niveau.PAROISSE):
            raise CourrierRefuse("Niveau de bureaux inconnu.")
        for u in permis.values():
            if u.niveau == niveau:
                choisis[u.cle] = u
    visibles = membres_visibles(unite)
    liste_membres = []
    for m in membres or []:
        if m.statut in SORTIS or not visibles.filter(pk=m.pk).exists():
            raise CourrierRefuse("Un des membres choisis ne peut pas recevoir ce courrier.")
        if m not in liste_membres:
            liste_membres.append(m)
    if not choisis and not liste_membres:
        raise CourrierRefuse("Choisissez au moins un destinataire (bureau ou membre).")
    return list(choisis.values()), liste_membres


def destinataires_directs(courrier: Courrier):
    return courrier.destinataires.filter(transmis_par="").select_related("membre")


def libelle_destinataires(courrier: Courrier, avec_membres: bool = True, membre=None) -> str:
    """Texte « Destinataire ».

    Les noms des membres destinataires ne sont montrés qu'à l'expéditeur et au Bureau national
    (`avec_membres`) ; un membre destinataire ne voit que son propre nom (un membre ne voit jamais
    un autre membre).
    """
    if courrier.communique:
        return "À l'attention de tous les bureaux"
    directs = destinataires_directs(courrier)
    bureaux = [d.libelle for d in directs.filter(type=TypeDestinataire.BUREAU)[:4]]
    nb_bureaux = directs.filter(type=TypeDestinataire.BUREAU).count()
    membres = directs.filter(type=TypeDestinataire.MEMBRE)
    nb_membres = membres.count()
    if avec_membres:
        if nb_bureaux + nb_membres > 3:
            morceaux = []
            if nb_bureaux:
                morceaux.append(f"{nb_bureaux} bureaux")
            if nb_membres:
                morceaux.append(f"{nb_membres} membres")
            return "À l'attention de " + " et ".join(morceaux) + " (liste en annexe)"
        return " ; ".join(bureaux + [d.libelle for d in membres])
    morceaux = bureaux if nb_bureaux <= 3 else [f"{nb_bureaux} bureaux"]
    autres, lui = nb_membres, False
    if membre is not None and membres.filter(membre=membre).exists():
        morceaux.append(membre.nom_complet)
        autres, lui = autres - 1, True
    if autres:
        morceaux.append(f"{autres} autre(s) membre(s)" if lui else f"{autres} membre(s)")
    return " ; ".join(morceaux)


def _libelle_bureau(u: Unite) -> str:
    if u.niveau == Niveau.NATIONAL:
        return "Bureau National de Commandement"
    nom = _nom_propre(u)
    return {
        Niveau.PAROISSE: f"Bureau de l'unité paroissiale de {nom}",
        Niveau.CIRCUIT: f"Bureau de la section circuit de {nom}",
        Niveau.REGION: f"Bureau régional de coordination — {nom}",
    }[u.niveau]


# --- Préparation ---------------------------------------------------------------------------------
def _controler_preparateur(unite: Unite, par) -> None:
    if unite not in unites_courrier(par):
        raise CourrierRefuse("Vous ne pouvez pas préparer de courrier pour ce bureau.")


def _contenu(mode, texte, fichier, courrier=None) -> tuple[str, str | None]:
    texte = (texte or "").strip()
    if mode == Mode.REDIGE:
        if not texte:
            raise CourrierRefuse("Le texte du courrier est vide.")
        return texte, None
    if mode != Mode.IMPORTE:
        raise CourrierRefuse("Façon de rédiger inconnue.")
    if fichier is None:
        if courrier is not None and courrier.fichier:
            return texte, None
        raise CourrierRefuse("Joignez le fichier du courrier (photo, scan ou PDF).")
    return texte, type_fichier(fichier)


@transaction.atomic
def preparer(
    *,
    unite: Unite,
    nature: str,
    objet: str,
    par,
    texte: str = "",
    mode: str = Mode.REDIGE,
    fichier=None,
    lieu: str = "",
    numero_ordre: int | None = None,
    bureaux=(),
    niveaux=(),
    membres=(),
    pieces=(),
) -> Courrier:
    _controler_preparateur(unite, par)
    if nature not in Nature.values:
        raise CourrierRefuse("Nature du courrier inconnue.")
    objet = (objet or "").strip()
    if not objet:
        raise CourrierRefuse("L'objet du courrier est obligatoire.")
    texte, extension = _contenu(mode, texte, fichier)
    destinataires_bureaux, destinataires_membres = _destinataires(unite, bureaux, niveaux, membres)
    if len(pieces) > PIECES_MAX:
        raise CourrierRefuse(f"{PIECES_MAX} pièces jointes au plus.")
    extensions_pieces = [type_fichier(p) for p in pieces]
    annee = timezone.localdate().year
    numero_ordre = numero_ordre or proposer_numero(unite, annee)
    _verifier_numero(unite, annee, numero_ordre)
    c = Courrier(
        nature=nature,
        mode=mode,
        expediteur_cle=unite.cle,
        expediteur_libelle=nom_bureau(unite),
        annee=annee,
        numero_ordre=numero_ordre,
        lieu=(lieu or "").strip()[:100] or lieu_par_defaut(unite),
        objet=objet[:250],
        texte=texte,
        prepare_par=par,
    )
    if extension:
        c.fichier.save(
            _nom_de_fichier(fichier.name, extension),
            _contenu_nettoye(fichier, extension),
            save=False,
        )
    c.save()
    for u in destinataires_bureaux:
        Destinataire.objects.create(
            courrier=c, type=TypeDestinataire.BUREAU, unite_cle=u.cle, libelle=_libelle_bureau(u)
        )
    for m in destinataires_membres:
        Destinataire.objects.create(
            courrier=c, type=TypeDestinataire.MEMBRE, membre=m, libelle=m.nom_complet
        )
    for p, ext in zip(pieces, extensions_pieces, strict=True):
        pj = PieceJointe(courrier=c, nom=p.name[:200])
        pj.fichier.save(_nom_de_fichier(p.name, ext), _contenu_nettoye(p, ext), save=True)
    _journal(par, "courrier_prepare", unite=unite.cle, courrier=c.pk, objet=c.objet)
    _avertir_signataires(c, unite)
    return c


def _avertir_signataires(c: Courrier, unite: Unite) -> None:
    from apps.bureaux.perimetre import signataires_courrier
    from apps.notifications.services import notifier

    comptes = [x for x in signataires_courrier(unite) if x.pk != c.prepare_par_id]
    lien = f"/courrier/c/{c.pk}/"
    message = f"Courrier à signer : « {c.objet} »."
    transaction.on_commit(lambda: notifier(comptes, message, lien))


def _verrouiller(courrier: Courrier) -> Courrier:
    return Courrier.objects.select_for_update().get(pk=courrier.pk)


@transaction.atomic
def modifier(
    courrier: Courrier,
    *,
    objet: str,
    par,
    texte: str = "",
    fichier=None,
    lieu: str | None = None,
    numero_ordre: int | None = None,
) -> Courrier:
    """Le préparateur reprend un courrier pas encore envoyé (en attente ou renvoyé)."""
    c = _verrouiller(courrier)
    unite = unite_expeditrice(c)
    if unite is None:
        raise CourrierRefuse("Bureau expéditeur introuvable.")
    _controler_preparateur(unite, par)
    if c.etat not in (Etat.A_SIGNER, Etat.A_CORRIGER):
        raise CourrierRefuse("Ce courrier n'est plus modifiable.")
    objet = (objet or "").strip()
    if not objet:
        raise CourrierRefuse("L'objet du courrier est obligatoire.")
    texte, extension = _contenu(c.mode, texte, fichier, courrier=c)
    if numero_ordre:
        _verifier_numero(unite, c.annee, numero_ordre, sauf=c)
        c.numero_ordre = numero_ordre
    c.objet, c.texte = objet[:250], texte
    if lieu is not None and lieu.strip():
        c.lieu = lieu.strip()[:100]
    if extension:
        c.fichier.save(
            _nom_de_fichier(fichier.name, extension),
            _contenu_nettoye(fichier, extension),
            save=False,
        )
    revenu = c.etat == Etat.A_CORRIGER
    c.etat, c.motif_renvoi = Etat.A_SIGNER, ""
    c.version += 1  # le signataire doit relire la nouvelle version
    c.save()
    _journal(par, "courrier_modifie", unite=unite.cle, courrier=c.pk, objet=c.objet)
    if revenu:
        _avertir_signataires(c, unite)
    return c


@transaction.atomic
def annuler(courrier: Courrier, *, par) -> Courrier:
    c = _verrouiller(courrier)
    unite = unite_expeditrice(c)
    if unite is None or unite not in unites_courrier(par):
        raise CourrierRefuse("Vous ne pouvez pas abandonner ce courrier.")
    if c.etat not in (Etat.A_SIGNER, Etat.A_CORRIGER):
        raise CourrierRefuse("Un courrier envoyé ne s'abandonne pas.")
    c.etat = Etat.ANNULE
    c.save(update_fields=["etat"])
    _journal(par, "courrier_abandonne", unite=unite.cle, courrier=c.pk, objet=c.objet)
    return c


# --- Signature -----------------------------------------------------------------------------------
def _image_signature(fichier) -> ContentFile:
    """PNG nettoyé, fond blanc rendu transparent, 900 × 360 pixels au plus."""
    if type_fichier(fichier) == "pdf":
        raise CourrierRefuse("La signature doit être une image JPEG ou PNG.")
    image = Image.open(fichier)
    image.load()
    image = image.convert("RGBA")
    image.thumbnail((900, 360))
    r, g, b, a = image.split()
    clair = ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 0 if v > 225 else 255)
    image.putalpha(ImageChops.multiply(a, clair))
    sortie = io.BytesIO()
    image.save(sortie, "PNG")
    return ContentFile(sortie.getvalue(), name="signature.png")


@transaction.atomic
def deposer_signature(compte, fichier) -> SignatureDeposee:
    """Le signataire dépose lui-même l'image de sa signature (personne d'autre ne le peut)."""
    if not peut_deposer_signature(compte):
        raise CourrierRefuse(
            "Seuls le Président, les Chefs et les Secrétaires en fonction déposent une signature."
        )
    contenu = _image_signature(fichier)
    Compte.objects.select_for_update().filter(pk=compte.pk).first()  # dépôts simultanés
    remplacee = SignatureDeposee.objects.filter(compte=compte, active=True).update(active=False)
    sig = SignatureDeposee(compte=compte)
    sig.image.save(f"signature-{compte.pk}.png", contenu, save=True)
    _journal(compte, "signature_deposee", remplacement=bool(remplacee))
    return sig


def signature_active(compte) -> SignatureDeposee | None:
    return SignatureDeposee.objects.filter(compte=compte, active=True).first()


def peut_signer(compte, courrier: Courrier):
    unite = unite_expeditrice(courrier)
    return qualite_signataire(compte, unite) if unite is not None else None


@transaction.atomic
def valider(courrier: Courrier, *, par, version: int | None = None) -> Courrier:
    """Signature : le courrier reçoit son numéro définitif, la signature du validateur et part."""
    c = _verrouiller(courrier)
    unite = unite_expeditrice(c)
    qualite = qualite_signataire(par, unite) if unite is not None else None
    if qualite is None:
        raise CourrierRefuse(
            "Seul le signataire du bureau (Président ou Chef ; le Secrétaire pour ordre) valide."
        )
    if c.etat != Etat.A_SIGNER:
        raise CourrierRefuse("Ce courrier n'attend pas de signature.")
    sig = signature_active(par)
    if sig is None:
        raise CourrierRefuse(
            "Déposez d'abord l'image de votre signature (rubrique « Ma signature »)."
        )
    if version is not None and version != c.version:
        raise CourrierRefuse(
            "Le courrier a été modifié depuis que vous l'avez ouvert : relisez-le avant de signer."
        )
    annee = timezone.localdate().year
    if c.annee != annee:  # préparé en décembre, signé en janvier : numéro de la nouvelle année
        c.annee, c.numero_ordre = annee, proposer_numero(unite, annee)
    elif (
        Courrier.objects.filter(
            expediteur_cle=c.expediteur_cle,
            annee=c.annee,
            numero_ordre=c.numero_ordre,
            etat=Etat.ENVOYE,
        )
        .exclude(pk=c.pk)
        .exists()
    ):
        c.numero_ordre = proposer_numero(unite, annee)  # numéro pris entre-temps : le suivant
    membre = getattr(par, "membre", None)
    c.etat = Etat.ENVOYE
    c.numero = numero_complet(unite, c.numero_ordre, c.annee)
    c.signe_par = par
    c.qualite = Qualite.TITULAIRE if qualite[0] == "titulaire" else Qualite.PO
    c.fonction_signataire = qualite[1]
    c.nom_signataire = membre.nom_complet if membre is not None else str(par)
    c.signature = sig
    c.date_envoi = timezone.now()
    try:
        with transaction.atomic():
            c.save()
    except IntegrityError as e:
        raise CourrierRefuse(
            "Un autre courrier vient de prendre ce numéro : cliquez de nouveau sur « Signer »."
        ) from e
    _journal(par, "courrier_envoye", unite=unite.cle, courrier=c.pk, numero=c.numero, objet=c.objet)
    texte, pk = c.texte, c.pk
    transaction.on_commit(lambda: _apprendre_mots(texte))
    transaction.on_commit(lambda: _prevenir_destinataires(Courrier.objects.get(pk=pk)))
    return c


def _prevenir_destinataires(c: Courrier) -> None:
    """Après l'envoi (hors verrou) : responsables des bureaux et membres destinataires."""
    from apps.bureaux.perimetre import titulaires_gestion_par_cle
    from apps.notifications.services import notifier

    nature = "Communiqué" if c.communique else "Courrier"
    message = f"{nature} reçu de {c.expediteur_libelle} : « {c.objet} » (n° {c.numero})."
    lien = f"/courrier/c/{c.pk}/"
    lignes = c.destinataires.select_related("membre__compte")
    cles = [d.unite_cle for d in lignes if d.type == TypeDestinataire.BUREAU]
    comptes = [compte for liste in titulaires_gestion_par_cle(cles).values() for compte in liste]
    comptes += [
        d.membre.compte
        for d in lignes
        if d.type == TypeDestinataire.MEMBRE and d.membre and d.membre.compte_id
    ]
    notifier(comptes, message, lien)


@transaction.atomic
def renvoyer(courrier: Courrier, *, motif: str, par) -> Courrier:
    """Le signataire renvoie le courrier au préparateur pour correction."""
    c = _verrouiller(courrier)
    if peut_signer(par, c) is None:
        raise CourrierRefuse("Seul un signataire du bureau renvoie un courrier.")
    if c.etat != Etat.A_SIGNER:
        raise CourrierRefuse("Ce courrier n'attend pas de signature.")
    motif = (motif or "").strip()
    if not motif:
        raise CourrierRefuse("Indiquez ce qu'il faut corriger.")
    c.etat, c.motif_renvoi = Etat.A_CORRIGER, motif[:300]
    c.save(update_fields=["etat", "motif_renvoi"])
    _journal(par, "courrier_renvoye", unite=c.expediteur_cle, courrier=c.pk, motif=c.motif_renvoi)
    if c.prepare_par_id and c.prepare_par_id != par.pk:
        from apps.notifications.services import notifier

        comptes, lien = [c.prepare_par], f"/courrier/c/{c.pk}/"
        message = f"Courrier à corriger : « {c.objet} » ({c.motif_renvoi})."
        transaction.on_commit(lambda: notifier(comptes, message, lien))
    return c


# --- Réception -----------------------------------------------------------------------------------
def destinataires_du_compte(compte, courrier: Courrier) -> list[Destinataire]:
    """Lignes de destinataire que ce compte représente (son bureau, ou lui-même)."""
    if not courrier.envoye:
        return []
    cles = [u.cle for u in unites_courrier(compte)]
    return list(
        courrier.destinataires.filter(
            Q(type=TypeDestinataire.BUREAU, unite_cle__in=cles)
            | Q(type=TypeDestinataire.MEMBRE, membre__compte=compte)
        )
    )


def marquer_recus(destinataires, compte) -> None:
    """Accusé de réception : le courrier est apparu dans la boîte du responsable."""
    pks = [d.pk for d in destinataires if d.recu_le is None]
    if pks:
        Destinataire.objects.filter(pk__in=pks, recu_le__isnull=True).update(recu_le=timezone.now())


def ouvrir(destinataire: Destinataire, compte) -> None:
    """Accusé de lecture : la première ouverture est gardée."""
    maintenant = timezone.now()
    Destinataire.objects.filter(pk=destinataire.pk, recu_le__isnull=True).update(recu_le=maintenant)
    Destinataire.objects.filter(pk=destinataire.pk, lu_le__isnull=True).update(
        lu_le=maintenant, lu_par=compte
    )


@transaction.atomic
def accuser(destinataire: Destinataire, *, par) -> Destinataire:
    """Bouton « Courrier reçu »."""
    d = Destinataire.objects.select_for_update().select_related("courrier").get(pk=destinataire.pk)
    if d.pk not in {x.pk for x in destinataires_du_compte(par, d.courrier)}:
        raise CourrierRefuse("Ce courrier ne vous est pas adressé.")
    if d.accuse_le is None:
        ouvrir(d, par)
        Destinataire.objects.filter(pk=d.pk).update(accuse_le=timezone.now(), accuse_par=par)
        _journal(par, "courrier_accuse", unite=d.unite_cle, courrier=d.courrier_id)
        d.refresh_from_db()
    return d


@transaction.atomic
def transmettre_aux_membres(courrier: Courrier, unite: Unite, *, par) -> int:
    """La paroisse transmet un communiqué reçu à ses membres (actifs et en sanction)."""
    if unite.niveau != Niveau.PAROISSE or unite not in unites_courrier(par):
        raise CourrierRefuse("Seul le bureau de la paroisse transmet à ses membres.")
    c = _verrouiller(courrier)
    if not (c.envoye and c.communique):
        raise CourrierRefuse("Seul un communiqué envoyé se transmet aux membres.")
    if not c.destinataires.filter(type=TypeDestinataire.BUREAU, unite_cle=unite.cle).exists():
        raise CourrierRefuse("Ce communiqué n'a pas été adressé à votre paroisse.")
    deja = set(
        c.destinataires.filter(type=TypeDestinataire.MEMBRE).values_list("membre", flat=True)
    )
    nouveaux = [
        Destinataire(
            courrier=c,
            type=TypeDestinataire.MEMBRE,
            membre=m,
            libelle=m.nom_complet,
            transmis_par=unite.cle,
        )
        for m in membres_visibles(unite)
        .exclude(statut__in=SORTIS)
        .exclude(pk__in=deja)
        .select_related("compte")
    ]
    Destinataire.objects.bulk_create(nouveaux)
    _journal(par, "courrier_transmis", unite=unite.cle, courrier=c.pk, nombre=len(nouveaux))
    from apps.notifications.services import notifier

    comptes = [d.membre.compte for d in nouveaux if d.membre.compte_id]
    message = f"Communiqué transmis par {unite.libelle} : « {c.objet} »."
    lien = f"/courrier/c/{c.pk}/"
    transaction.on_commit(lambda: notifier(comptes, message, lien))
    return len(nouveaux)


# --- Consultation --------------------------------------------------------------------------------
def peut_voir(compte, courrier: Courrier) -> bool:
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return False
    cles = {u.cle for u in unites_courrier(compte)}
    if courrier.expediteur_cle in cles:
        return True
    if courrier.etat in (Etat.A_SIGNER, Etat.A_CORRIGER) and peut_signer(compte, courrier):
        return True
    # Décision du 18/11/2026 : pas de droit de regard du Bureau national sur les courriers des
    # autres niveaux ; il ne voit que ce qu'il envoie ou ce qui lui est adressé.
    return bool(destinataires_du_compte(compte, courrier))


def courriers_recus(unite: Unite):
    return (
        Courrier.objects.filter(
            etat=Etat.ENVOYE,
            destinataires__type=TypeDestinataire.BUREAU,
            destinataires__unite_cle=unite.cle,
        )
        .distinct()
        .order_by("-date_envoi")
    )


def courriers_envoyes(unite: Unite):
    return Courrier.objects.filter(expediteur_cle=unite.cle).order_by("-date_preparation")


def courriers_a_signer(compte):
    """Courriers en attente que ce compte peut signer."""
    from apps.bureaux.models import Mandat
    from apps.bureaux.perimetre import SIGNATAIRES_PO, SIGNATAIRES_TITULAIRES
    from apps.membres.models import Statut

    noms = (*SIGNATAIRES_TITULAIRES.values(), *SIGNATAIRES_PO.values())
    mandats = Mandat.objects.en_cours().filter(
        membre__compte=compte, membre__statut=Statut.ACTIF, fonction__nom__in=noms
    )
    cles = set()
    for m in mandats.select_related("fonction"):
        cles.add(
            "national"
            if m.fonction.niveau == Niveau.NATIONAL
            else f"{m.fonction.niveau}-{m.unite.pk}"
        )
    return Courrier.objects.filter(expediteur_cle__in=cles, etat=Etat.A_SIGNER)


def courriers_du_membre(membre):
    return (
        Courrier.objects.filter(
            etat=Etat.ENVOYE,
            destinataires__type=TypeDestinataire.MEMBRE,
            destinataires__membre=membre,
        )
        .distinct()
        .order_by("-date_envoi")
    )


# --- Clavier goun --------------------------------------------------------------------------------
MOT = re.compile(r"(?:[^\W\d_]|[̀-ͯ])+")
LONGUEUR_MIN = 3


FRANCAIS = set("abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüÿœæ")
SEUIL_COURRIERS = 2  # un mot appris n'est proposé qu'après 2 courriers différents


def _mots(texte: str) -> list[str]:
    """Mots goun du texte : au moins une lettre hors de l'alphabet français (ẹ, ọ, ɖ, ɛ, á…).

    Les mots français et les noms propres (écrits avec une majuscule) ne sont pas appris : les
    propositions ne doivent rien révéler des courriers des autres bureaux.
    """
    texte = unicodedata.normalize("NFC", texte or "")
    resultat = []
    for m in MOT.findall(texte):
        if not (LONGUEUR_MIN <= len(m) <= 60) or m[0] != m[0].lower():
            continue
        if any(ch not in FRANCAIS for ch in m.lower()):
            resultat.append(m.lower())
    return resultat


def _apprendre_mots(texte: str) -> None:
    """Chaque courrier compte une fois par mot (ordre trié : pas de verrous croisés)."""
    for mot in sorted(set(_mots(texte))):
        obj, cree = MotClavier.objects.get_or_create(
            mot=mot, defaults={"origine": OrigineMot.APPRIS, "nombre": 1}
        )
        if not cree:
            MotClavier.objects.filter(pk=obj.pk).update(nombre=F("nombre") + 1)


def mots_appris_proposes(limite: int = 500):
    return MotClavier.objects.filter(
        actif=True, origine=OrigineMot.APPRIS, nombre__gte=SEUIL_COURRIERS
    ).order_by("-nombre", "mot")[:limite]


def _cle(mot: str) -> str:
    from apps.courrier.models import cle_de_recherche

    return cle_de_recherche(mot)


def proposer_mots(debut: str, limite: int = 8) -> list[str]:
    """Mots qui commencent par `debut`, sans tenir compte des points ni des tons : liste du BN
    d'abord, puis lexique et mots appris (après deux courriers), du plus fréquent au moins."""
    from django.db.models import Case, IntegerField, Value, When

    cle = _cle(debut)
    if not cle:
        return []
    deja = unicodedata.normalize("NFC", debut).lower()
    mots = (
        MotClavier.objects.filter(actif=True, cle__startswith=cle[:60])
        .filter(~Q(origine=OrigineMot.APPRIS) | Q(nombre__gte=SEUIL_COURRIERS))
        .exclude(mot=deja)
        .annotate(
            rang=Case(
                When(origine=OrigineMot.BN, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("rang", "-nombre", "mot")
    )
    candidats = list(mots.values_list("mot", "rang")[:60])
    # Les mots qui gardent les points tapés (« tọ » → tọn avant to) passent devant.
    tape = _sans_tons(deja)
    if "\u0323" in unicodedata.normalize("NFD", tape):  # point tapé : on le respecte d'abord
        candidats.sort(key=lambda p: (p[1], not _sans_tons(p[0]).startswith(tape)))
    return [mot for mot, _rang in candidats[:limite]]


def _sans_tons(mot: str) -> str:
    """Retire les tons mais garde le point souscrit (ẹ, ọ, ṣ)."""
    decompose = unicodedata.normalize("NFD", mot)
    garde = "".join(c for c in decompose if unicodedata.category(c) != "Mn" or c == "\u0323")
    return unicodedata.normalize("NFC", garde)


@transaction.atomic
def enregistrer_mots_bn(texte: str, *, par) -> int:
    """Liste du BN : un mot (ou une courte expression) par ligne ; remplace la liste précédente."""
    lignes = []
    for ligne in (texte or "").splitlines():
        mot = unicodedata.normalize("NFC", ligne.strip()).lower()[:60]
        if mot and mot not in lignes:
            lignes.append(mot)
    MotClavier.objects.filter(origine=OrigineMot.BN).exclude(mot__in=lignes).update(
        origine=OrigineMot.APPRIS
    )
    for mot in lignes:
        MotClavier.objects.update_or_create(
            mot=mot, defaults={"origine": OrigineMot.BN, "actif": True}
        )
    _journal(par, "clavier_modifie", unite="national", mots=len(lignes))
    return len(lignes)


def masquer_mot(mot: str, *, par) -> None:
    MotClavier.objects.filter(mot=unicodedata.normalize("NFC", mot).lower()).update(actif=False)
    _journal(par, "clavier_modifie", unite="national", masque=mot)


def enregistrer_lettres(texte: str, *, par) -> ReglagesClavier:
    r = ReglagesClavier.courant()
    lettres = []
    for x in (texte or "").split():
        x = unicodedata.normalize("NFC", x)
        if unicodedata.category(x[0]) == "Mn":  # ton seul : touche « ◌́ »
            x = "\u25cc" + x
        if len(x) <= 4:
            lettres.append(x)
    if not lettres:
        raise CourrierRefuse("Indiquez au moins une lettre.")
    r.lettres = " ".join(lettres)
    r.save()
    _journal(par, "clavier_modifie", unite="national", lettres=r.lettres)
    return r
