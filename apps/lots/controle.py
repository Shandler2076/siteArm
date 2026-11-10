"""Normalisation et vérification des lignes d'un lot (mêmes règles que l'enregistrement)."""

import datetime
import re

from django.db.models import Q

from apps.lots.colonnes import COLONNES, PAR_CHAMP
from apps.lots.models import EtatLigne, LigneLot
from apps.membres.forms import valider_futur_membre
from apps.membres.models import Categorie, SituationMatrimoniale, cle_nom
from apps.organisation.models import Paroisse, Region

MESSAGE_DATE = "date invalide, écrivez JJ/MM/AAAA"
VIDE = "Ce champ ne peut pas être vide."
DATE_TEXTE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
# Une vraie cellule date d'Excel est rangée en base au format ISO (« 1985-03-12T00:00:00 »).
DATE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(T00:00:00)?$")
CHAMPS_NUMEROS = ("telephone", "whatsapp", "urgence_telephone", "npi")
MESSAGE_NOMBRE = (
    "saisi comme un nombre : le 0 initial a pu être perdu. Écrivez-le comme du texte "
    "(cellule au format Texte), par exemple 0197000000"
)


def _texte(valeur) -> str:
    if valeur is None:
        return ""
    if isinstance(valeur, float) and valeur.is_integer():
        valeur = int(valeur)
    return re.sub(r"\s+", " ", str(valeur)).strip()


def _date(valeur):
    if isinstance(valeur, datetime.datetime):
        return valeur.date()
    if isinstance(valeur, datetime.date):
        return valeur
    texte = _texte(valeur)
    iso = DATE_ISO.match(texte)
    if iso:
        annee, mois, jour = (int(x) for x in iso.groups()[:3])
        return datetime.date(annee, mois, jour)
    m = DATE_TEXTE.match(texte)
    if not m:
        raise ValueError
    jour, mois, annee = (int(x) for x in m.groups())
    return datetime.date(annee, mois, jour)


def paroisses_de(region: Region) -> dict[str, Paroisse]:
    """Paroisses actives de la région, par nom normalisé (chargées une seule fois par lot)."""
    return {
        cle_nom(p.nom): p
        for p in Paroisse.objects.filter(circuit__region=region, active=True).select_related(
            "circuit__region"
        )
    }


def _par_libelle(choix, valeur: str):
    cle = cle_nom(valeur)
    for code, libelle in choix:
        if cle in (cle_nom(libelle), cle_nom(code)):
            return code
    raise ValueError


def normaliser_ligne(
    brutes: dict, region: Region, paroisses: dict[str, Paroisse] | None = None
) -> tuple[dict, list[str]]:
    """Valeurs lues → valeurs prêtes pour `Membre` (JSON) et erreurs de conversion."""
    donnees, erreurs = {}, []
    if paroisses is None:
        paroisses = paroisses_de(region)

    def erreur(champ, message):
        erreurs.append(f"{PAR_CHAMP[champ].entete} : {message}")

    for colonne in COLONNES:
        brut = brutes.get(colonne.entete)
        texte = _texte(brut)
        champ = colonne.champ
        if not texte and not isinstance(brut, datetime.date):
            if colonne.obligatoire:
                erreur(champ, VIDE)
            elif champ == "categorie":
                donnees[champ] = Categorie.ACTIF
            elif champ == "date_naissance":
                donnees[champ] = None
            else:
                donnees[champ] = ""
            continue
        if champ in CHAMPS_NUMEROS and isinstance(brut, (int, float)):
            erreur(champ, MESSAGE_NOMBRE)
            continue
        try:
            if champ == "date_naissance":
                donnees[champ] = _date(brut).isoformat()
            elif champ == "sexe":
                donnees[champ] = texte.upper()
            elif champ == "annee_integration":
                if not re.fullmatch(r"\d{4}", texte):
                    raise ValueError
                donnees[champ] = int(texte)
            elif champ == "situation_matrimoniale":
                donnees[champ] = _par_libelle(SituationMatrimoniale.choices, texte)
            elif champ == "categorie":
                donnees[champ] = _par_libelle(Categorie.choices, texte)
            elif champ == "paroisse_integration":
                trouvee = paroisses.get(cle_nom(texte))
                if trouvee is None:
                    erreur(champ, f"« {texte} » n'existe pas dans la région {region.nom}")
                    continue
                donnees[champ] = trouvee.pk
            else:
                donnees[champ] = texte
        except ValueError:
            messages = {
                "date_naissance": MESSAGE_DATE,
                "annee_integration": "nombre à 4 chiffres attendu (ex. 2015)",
                "situation_matrimoniale": f"valeur inconnue « {texte} » (choisissez dans la liste)",
                "categorie": f"valeur inconnue « {texte} » (choisissez dans la liste)",
            }
            erreur(champ, messages[champ])
    return donnees, erreurs


def donnees_pour_membre(donnees: dict) -> tuple[dict, Paroisse | None, int | None]:
    """JSON de la ligne → champs du modèle `Membre`, paroisse et année d'intégration."""
    champs = {
        k: v for k, v in donnees.items() if k not in ("paroisse_integration", "annee_integration")
    }
    if champs.get("date_naissance"):
        champs["date_naissance"] = datetime.date.fromisoformat(champs["date_naissance"])
    pk = donnees.get("paroisse_integration")
    paroisse = (
        Paroisse.objects.filter(pk=pk, active=True).select_related("circuit__region").first()
        if pk
        else None
    )
    return champs, paroisse, donnees.get("annee_integration")


MESSAGE_NPI = "Ce NPI est déjà utilisé par un autre membre."


def verifier_ligne(
    ligne: LigneLot,
    paroisses: dict[str, Paroisse] | None = None,
    enregistrer: bool = True,
    npi_existants: set[str] | None = None,
) -> None:
    """Vérifie une ligne. `npi_existants` (contrôle du lot) évite une requête par ligne."""
    if ligne.etat == EtatLigne.ECARTEE:
        return
    region = ligne.lot.region
    paroisses = paroisses_de(region) if paroisses is None else paroisses
    donnees, erreurs = normaliser_ligne(ligne.brutes, region, paroisses)
    champs = {
        k: v for k, v in donnees.items() if k not in ("paroisse_integration", "annee_integration")
    }
    if champs.get("date_naissance"):
        champs["date_naissance"] = datetime.date.fromisoformat(champs["date_naissance"])
    if donnees.get("annee_integration") is not None:
        champs["annee_integration"] = donnees["annee_integration"]
    paroisse = next(
        (p for p in paroisses.values() if p.pk == donnees.get("paroisse_integration")), None
    )
    en_erreur = {c.champ for c in COLONNES if any(e.startswith(c.entete + " :") for e in erreurs)}
    exclure = [c.champ for c in COLONNES if c.champ not in donnees or c.champ in en_erreur]
    # La paroisse vient déjà de la base : inutile de la revérifier ligne par ligne.
    exclure += ["paroisse_integration", "region_integration"]
    erreurs_modele = valider_futur_membre(
        champs, paroisse, exclure=exclure, verifier_contraintes=npi_existants is None
    )
    npi = donnees.get("npi")
    if npi_existants is not None and npi and npi in npi_existants and "npi" not in en_erreur:
        erreurs_modele.setdefault("npi", []).append(MESSAGE_NPI)
    for champ, messages in erreurs_modele.items():
        entete = PAR_CHAMP[champ].entete if champ in PAR_CHAMP else None
        for m in messages:
            erreurs.append(f"{entete} : {m}" if entete else m)
    ordre = {c.entete: i for i, c in enumerate(COLONNES)}
    erreurs.sort(key=lambda e: ordre.get(e.split(" : ")[0], len(ordre)))
    ligne.donnees = donnees
    ligne.erreurs = erreurs
    ligne.doublons = []
    ligne.etat = EtatLigne.ERREUR if erreurs else EtatLigne.CORRECTE
    if enregistrer:
        ligne.save(update_fields=["donnees", "erreurs", "doublons", "etat"])


# --- Doublons et contrôle du lot ---------------------------------------------------------


def _cle_identite(donnees: dict) -> str:
    return f"{cle_nom(donnees.get('nom', ''))} | {cle_nom(donnees.get('prenoms', ''))}"


def _dates_compatibles(a, b) -> bool:
    return not a or not b or str(a) == str(b)


def controler_lot(lot) -> None:
    """Vérifie chaque ligne non écartée puis cherche les doublons (base et fichier).

    Tout se fait dans une transaction, sur le lot verrouillé, et uniquement en brouillon.
    """
    from collections import defaultdict

    from django.db import transaction

    from apps.lots.models import EtatLot, Lot
    from apps.membres.models import Membre

    with transaction.atomic():
        verrou = Lot.objects.select_for_update().select_related("region").get(pk=lot.pk)
        if verrou.etat != EtatLot.BROUILLON:
            return
        paroisses = paroisses_de(verrou.region)
        lignes = list(verrou.lignes.exclude(etat=EtatLigne.ECARTEE).order_by("numero"))
        anciens = {x.pk: (x.etat, list(x.doublons)) for x in lignes}
        npis_lus = {
            _texte(x.brutes.get(PAR_CHAMP["npi"].entete))
            for x in lignes
            if not isinstance(x.brutes.get(PAR_CHAMP["npi"].entete), (int, float))
        } - {""}
        npi_existants = set(Membre.objects.filter(npi__in=npis_lus).values_list("npi", flat=True))
        for ligne in lignes:
            ligne.lot = verrou
            verifier_ligne(ligne, paroisses, enregistrer=False, npi_existants=npi_existants)
        valides = [x for x in lignes if x.etat == EtatLigne.CORRECTE]

        # Doublons dans le fichier : regroupés par identité et par NPI (sans comparer 2 à 2).
        par_cle, par_npi = defaultdict(list), defaultdict(list)
        for x in valides:
            par_cle[_cle_identite(x.donnees)].append(x)
            if x.donnees.get("npi"):
                par_npi[x.donnees["npi"]].append(x)

        # Doublons avec les membres existants : une seule requête pour tout le lot.
        cles = list(par_cle)
        npis = list(par_npi)
        existants = list(
            Membre.objects.filter(Q(cle_identite__in=cles) | Q(npi__in=npis)).values(
                "matricule", "cle_identite", "date_naissance", "npi"
            )
        )
        for x in valides:
            d = x.donnees
            trouves = [
                m["matricule"]
                for m in existants
                if (d.get("npi") and m["npi"] == d["npi"])
                or (
                    m["cle_identite"] == _cle_identite(d)
                    and _dates_compatibles(m["date_naissance"], d.get("date_naissance"))
                )
            ]
            autres = {
                a.numero
                for a in par_cle[_cle_identite(d)]
                if _dates_compatibles(a.donnees.get("date_naissance"), d.get("date_naissance"))
            } | {a.numero for a in par_npi.get(d.get("npi") or "", [])}
            autres.discard(x.numero)
            trouves += [f"ligne {n}" for n in sorted(autres)]
            if trouves:
                etat_avant, doublons_avant = anciens[x.pk]
                garde = etat_avant == EtatLigne.GARDEE and sorted(doublons_avant) == sorted(trouves)
                x.etat = EtatLigne.GARDEE if garde else EtatLigne.DOUBLON
                x.doublons = trouves
        LigneLot.objects.bulk_update(lignes, ["donnees", "erreurs", "doublons", "etat"])


def _json(brutes: dict) -> dict:
    return {
        k: (v.isoformat() if isinstance(v, (datetime.date, datetime.datetime)) else v)
        for k, v in brutes.items()
    }


def _ajouter_fichier(lot, fichier) -> None:
    """Archive le fichier déposé (les précédents restent consultables)."""
    from django.utils import timezone

    n = len(lot.fichiers)
    fichier.seek(0)
    lot.fichier.save(f"lot-{lot.pk}-{n}.xlsx", fichier, save=False)
    lot.fichiers = [
        *lot.fichiers,
        {"nom": fichier.name[:200], "chemin": lot.fichier.name, "date": timezone.now().isoformat()},
    ]
    lot.nom_fichier = fichier.name[:200]
    lot.save(update_fields=["fichier", "fichiers", "nom_fichier"])


def _remplir(lot, lignes) -> None:
    lot.lignes.all().delete()
    LigneLot.objects.bulk_create([LigneLot(lot=lot, numero=n, brutes=_json(b)) for n, b in lignes])


def creer_lot(*, region: Region, fichier, par):
    """Crée un lot en brouillon à partir du fichier. Aucun membre n'est créé."""
    from django.db import transaction

    from apps.lots.lecture import lire_classeur
    from apps.lots.models import Lot

    lignes = lire_classeur(fichier)  # contrôle de forme avant de créer quoi que ce soit
    with transaction.atomic():
        lot = Lot.objects.create(region=region, cree_par=par, nom_fichier=fichier.name[:200])
        _ajouter_fichier(lot, fichier)
        _remplir(lot, lignes)
    controler_lot(lot)
    return lot


def remplacer_fichier(lot, fichier, par) -> None:
    from django.db import transaction

    from apps.lots.lecture import lire_classeur
    from apps.lots.models import EtatLot, Lot

    lignes = lire_classeur(fichier)  # peut lever FichierInvalide : rien n'est modifié
    with transaction.atomic():
        verrou = Lot.objects.select_for_update().get(pk=lot.pk)
        if verrou.etat != EtatLot.BROUILLON:
            raise ValueError("Un lot validé ne peut plus être modifié.")
        _ajouter_fichier(verrou, fichier)
        _remplir(verrou, lignes)
    controler_lot(verrou)
    lot.refresh_from_db()
