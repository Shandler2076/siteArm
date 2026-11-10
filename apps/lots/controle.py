"""Normalisation et vérification des lignes d'un lot (mêmes règles que l'enregistrement)."""

import datetime
import re

from apps.lots.colonnes import COLONNES, PAR_CHAMP
from apps.lots.models import EtatLigne, LigneLot
from apps.membres.forms import valider_futur_membre
from apps.membres.models import Categorie, SituationMatrimoniale, cle_nom
from apps.organisation.models import Paroisse, Region

MESSAGE_DATE = "date invalide, écrivez JJ/MM/AAAA"
VIDE = "Ce champ ne peut pas être vide."
DATE_TEXTE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


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
    m = DATE_TEXTE.match(_texte(valeur))
    if not m:
        raise ValueError
    jour, mois, annee = (int(x) for x in m.groups())
    return datetime.date(annee, mois, jour)


def _par_libelle(choix, valeur: str):
    cle = cle_nom(valeur)
    for code, libelle in choix:
        if cle in (cle_nom(libelle), cle_nom(code)):
            return code
    raise ValueError


def normaliser_ligne(brutes: dict, region: Region) -> tuple[dict, list[str]]:
    """Valeurs lues → valeurs prêtes pour `Membre` (JSON) et erreurs de conversion."""
    donnees, erreurs = {}, []

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
                cle = cle_nom(texte)
                trouvee = next(
                    (
                        p
                        for p in Paroisse.objects.filter(circuit__region=region, active=True)
                        if cle_nom(p.nom) == cle
                    ),
                    None,
                )
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
    paroisse = Paroisse.objects.filter(pk=pk).first() if pk else None
    return champs, paroisse, donnees.get("annee_integration")


def verifier_ligne(ligne: LigneLot) -> None:
    if ligne.etat == EtatLigne.ECARTEE:
        return
    donnees, erreurs = normaliser_ligne(ligne.brutes, ligne.lot.region)
    champs, paroisse, annee = donnees_pour_membre(donnees)
    if annee is not None:
        champs["annee_integration"] = annee
    en_erreur = {c.champ for c in COLONNES if any(e.startswith(c.entete + " :") for e in erreurs)}
    exclure = [c.champ for c in COLONNES if c.champ not in donnees or c.champ in en_erreur]
    for champ, messages in valider_futur_membre(champs, paroisse, exclure=exclure).items():
        entete = PAR_CHAMP[champ].entete if champ in PAR_CHAMP else None
        for m in messages:
            erreurs.append(f"{entete} : {m}" if entete else m)
    ordre = {c.entete: i for i, c in enumerate(COLONNES)}
    erreurs.sort(key=lambda e: ordre.get(e.split(" : ")[0], len(ordre)))
    ligne.donnees = donnees
    ligne.erreurs = erreurs
    ligne.doublons = []
    ligne.etat = EtatLigne.ERREUR if erreurs else EtatLigne.CORRECTE
    ligne.save()


# --- Doublons et contrôle du lot ---------------------------------------------------------


def _cle_identite(donnees: dict) -> str:
    return f"{cle_nom(donnees.get('nom', ''))} | {cle_nom(donnees.get('prenoms', ''))}"


def _meme_personne(a: dict, b: dict) -> bool:
    if a.get("npi") and a.get("npi") == b.get("npi"):
        return True
    if _cle_identite(a) != _cle_identite(b):
        return False
    da, db = a.get("date_naissance"), b.get("date_naissance")
    return not da or not db or da == db


def controler_lot(lot) -> None:
    """Vérifie chaque ligne non écartée puis recherche les doublons (base et fichier)."""
    from apps.membres.services import doublons_possibles

    lignes = list(lot.lignes.exclude(etat=EtatLigne.ECARTEE).order_by("numero"))
    anciens = {ligne.pk: (ligne.etat, list(ligne.doublons)) for ligne in lignes}
    for ligne in lignes:
        verifier_ligne(ligne)
    valides = [ligne for ligne in lignes if ligne.etat == EtatLigne.CORRECTE]
    for ligne in valides:
        d = ligne.donnees
        date = datetime.date.fromisoformat(d["date_naissance"]) if d.get("date_naissance") else None
        trouves = [
            m.matricule
            for m in doublons_possibles(
                nom=d["nom"], prenoms=d["prenoms"], date_naissance=date, npi=d.get("npi", "")
            )
        ]
        trouves += [
            f"ligne {autre.numero}"
            for autre in valides
            if autre is not ligne and _meme_personne(d, autre.donnees)
        ]
        if not trouves:
            continue
        etat_avant, doublons_avant = anciens[ligne.pk]
        garde = etat_avant == EtatLigne.GARDEE and sorted(doublons_avant) == sorted(trouves)
        ligne.etat = EtatLigne.GARDEE if garde else EtatLigne.DOUBLON
        ligne.doublons = trouves
        ligne.save(update_fields=["etat", "doublons"])


def _remplir(lot, fichier) -> None:
    from apps.lots.lecture import lire_classeur

    lignes = lire_classeur(fichier)  # peut lever FichierInvalide : rien n'est modifié
    lot.lignes.all().delete()
    LigneLot.objects.bulk_create([LigneLot(lot=lot, numero=n, brutes=_json(b)) for n, b in lignes])
    controler_lot(lot)


def _json(brutes: dict) -> dict:
    return {
        k: (v.isoformat() if isinstance(v, (datetime.date, datetime.datetime)) else v)
        for k, v in brutes.items()
    }


def creer_lot(*, region: Region, fichier, par):
    """Crée un lot en brouillon à partir du fichier. Aucun membre n'est créé."""
    from django.db import transaction

    from apps.lots.lecture import lire_classeur
    from apps.lots.models import Lot

    lire_classeur(fichier)  # contrôle de forme avant de créer quoi que ce soit
    with transaction.atomic():
        lot = Lot.objects.create(region=region, cree_par=par, nom_fichier=fichier.name[:200])
        fichier.seek(0)
        lot.fichier.save(f"lot-{lot.pk}.xlsx", fichier, save=True)
        fichier.seek(0)
        _remplir(lot, fichier)
    return lot


def remplacer_fichier(lot, fichier, par) -> None:
    from django.db import transaction

    from apps.lots.models import EtatLot

    if lot.etat != EtatLot.BROUILLON:
        raise ValueError("Un lot validé ne peut plus être modifié.")
    with transaction.atomic():
        _remplir(lot, fichier)
        fichier.seek(0)
        lot.fichier.save(f"lot-{lot.pk}.xlsx", fichier, save=False)
        lot.nom_fichier = fichier.name[:200]
        lot.save()
