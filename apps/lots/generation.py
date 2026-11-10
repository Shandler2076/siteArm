"""Validation d'un lot : création de tous les membres en une seule transaction (tout ou rien)."""

from collections import Counter

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.lots.controle import controler_lot, donnees_pour_membre
from apps.lots.models import A_CREER, EtatLot, Lot
from apps.membres.models import Membre
from apps.membres.services import enregistrer_membre


class GenerationEchouee(Exception):
    pass


def _message(erreur: Exception) -> str:
    if isinstance(erreur, ValidationError):
        return " ".join(erreur.messages)
    return str(erreur)


def valider_lot(lot: Lot, par) -> list[Membre]:
    # Le contrôle est refait juste avant : un membre inscrit entre-temps, un autre lot déjà
    # validé ou une paroisse fermée sont détectés (et visibles sur l'écran de contrôle).
    lot_avant = Lot.objects.get(pk=lot.pk)
    if lot_avant.etat == EtatLot.BROUILLON:
        etats_avant = dict(lot_avant.lignes.values_list("numero", "etat"))
        controler_lot(lot_avant)
        if dict(lot_avant.lignes.values_list("numero", "etat")) != etats_avant:
            raise GenerationEchouee(
                "Des doublons ou des erreurs sont apparus depuis le contrôle : revérifiez le lot "
                "avant de le valider. Aucun membre n'a été créé."
            )
    with transaction.atomic():
        lot = Lot.objects.select_for_update().select_related("region").get(pk=lot.pk)
        if lot.etat != EtatLot.BROUILLON:
            raise GenerationEchouee("Ce lot est déjà validé.")
        if not lot.validable:
            raise GenerationEchouee(
                "Ce lot ne peut pas être validé : il reste des erreurs ou des doublons à trancher."
            )
        crees = []
        for ligne in lot.lignes.filter(etat__in=A_CREER).order_by("numero"):
            champs, paroisse, annee = donnees_pour_membre(ligne.donnees)
            try:
                with transaction.atomic():
                    membre = enregistrer_membre(
                        donnees=champs,
                        paroisse_integration=paroisse,
                        annee_integration=annee,
                        par=par,
                        notifier=False,
                        avec_mot_de_passe=False,
                    ).membre
            except Exception as e:  # noqa: BLE001 — toute erreur annule le lot entier
                raise GenerationEchouee(
                    f"Ligne {ligne.numero} : {_message(e)} Aucun membre n'a été créé."
                ) from e
            ligne.membre = membre
            ligne.save(update_fields=["membre"])
            crees.append(membre)
        lot.etat = EtatLot.VALIDE
        lot.valide_par = par
        lot.date_validation = timezone.now()
        lot.save(update_fields=["etat", "valide_par", "date_validation"])
        numero = lot.pk
        transaction.on_commit(lambda: _notifier_bureaux(crees, numero))
    return crees


def _notifier_bureaux(membres: list[Membre], numero_lot: int) -> None:
    from apps.bureaux.perimetre import Unite
    from apps.notifications.services import notifier_unite

    compte = Counter()
    for m in membres:
        p = m.paroisse_integration
        compte[Unite("paroisse", p)] += 1
        compte[Unite("circuit", p.circuit)] += 1
        compte[Unite("region", p.circuit.region)] += 1
    for unite, n in compte.items():
        texte = "1 nouveau membre" if n == 1 else f"{n} nouveaux membres"
        notifier_unite(unite, f"{texte} dans votre périmètre (lot n° {numero_lot}).")
