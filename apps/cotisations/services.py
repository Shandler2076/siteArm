"""Seuls points d'entrée qui écrivent les cotisations (cahier des charges § 16).

Paroisse : saisie (individuelle ou collecte) et annulation d'un versement en attente.
Circuit : validation ou refus. Circuit, région, national : parts reçues. BNC : réglages et
annulation d'un versement validé. Les droits sont vérifiés par les vues (gardien des périmètres).
"""

import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cotisations.models import (
    EtatVersement,
    MoisCotise,
    NiveauPart,
    ParametresCotisations,
    PartRecue,
    Tarif,
    Versement,
    premier_du_mois,
    tarif_parmi,
    tarifs,
)
from apps.cotisations.regles import mois_suivant, situation
from apps.membres.models import Membre

MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip
DELAI_RAPPEL_JOURS = 30


class CotisationRefusee(Exception):
    """Opération refusée ; le message s'affiche tel quel."""


def aujourdhui() -> datetime.date:
    return timezone.localdate()


def nom_mois(mois: datetime.date) -> str:
    return f"{MOIS[mois.month - 1]} {mois.year}"


def periode(mois: list[datetime.date]) -> str:
    """« janvier 2026 », « janvier à mars 2026 », « décembre 2026 à février 2027 »."""
    mois = sorted(mois)
    if not mois:
        return ""
    if len(mois) == 1:
        return nom_mois(mois[0])
    debut, fin = mois[0], mois[-1]
    if debut.year == fin.year:
        return f"{MOIS[debut.month - 1]} à {nom_mois(fin)}"
    return f"{nom_mois(debut)} à {nom_mois(fin)}"


def _journal(par, action, unite="", **details):
    from apps.journal.services import journaliser

    journaliser(par, action, unite=unite, **details)


def _cle_paroisse(paroisse) -> str:
    return f"paroisse-{paroisse.pk}"


def _notifier_unite(unite, message):
    from apps.bureaux.perimetre import titulaires_cotisations
    from apps.notifications.services import notifier

    transaction.on_commit(lambda: notifier(titulaires_cotisations(unite), message))


def _choisir_mois(membre, montant, mois_choisis, jour) -> list[tuple[datetime.date, int]]:
    """[(mois, montant du mois)] couverts par `montant` ; lève CotisationRefusee sinon."""
    depart = ParametresCotisations.courant().mois_depart
    if depart is None:
        raise CotisationRefusee(
            "Les cotisations ne sont pas encore ouvertes : le BNC doit fixer le mois de départ."
        )
    if montant is None or montant <= 0:
        raise CotisationRefusee("Le montant doit être positif.")
    courant = premier_du_mois(jour)
    fin_annee = courant.replace(month=12)
    s = situation(membre, courant)
    occupes = s.payes | s.en_attente
    debut = s.dus[0] if s.dus else max(depart, premier_du_mois(membre.date_enregistrement.date()))
    liste = tarifs()
    if mois_choisis:
        choisis = sorted({premier_du_mois(m) for m in mois_choisis})
        for m in choisis:
            if m < debut or m > fin_annee:
                raise CotisationRefusee(
                    f"{nom_mois(m).capitalize()} : ce mois n'est pas payable pour ce membre."
                )
            if m in occupes:
                raise CotisationRefusee(f"{nom_mois(m).capitalize()} : déjà payé ou en attente.")
        couverts = [(m, tarif_parmi(liste, m).montant) for m in choisis]
        if sum(x for _m, x in couverts) != montant:
            raise CotisationRefusee(
                f"Le montant ({montant} F) ne correspond pas aux mois cochés "
                f"({sum(x for _m, x in couverts)} F)."
            )
        return couverts
    candidats = [m for m in s.dus if m not in occupes]
    m = mois_suivant(courant)
    while m <= fin_annee:  # paiement d'avance : mois suivants de l'année en cours
        if m not in occupes:
            candidats.append(m)
        m = mois_suivant(m)
    couverts, reste = [], montant
    for m in candidats:
        prix = tarif_parmi(liste, m).montant
        if reste < prix:
            break
        couverts.append((m, prix))
        reste -= prix
    if reste or not couverts:
        prix = tarif_parmi(liste, courant).montant
        raise CotisationRefusee(
            f"Le montant ({montant} F) doit correspondre à un nombre entier de mois "
            f"({prix} F par mois), dans la limite des mois payables jusqu'en décembre."
        )
    return couverts


def _saisir(membre, montant, date_versement, par, mois=None) -> Versement:
    affectation = membre.affectation_actuelle
    if affectation is None:
        raise CotisationRefusee(f"{membre.nom_complet} n'est rattaché à aucune paroisse.")
    couverts = _choisir_mois(membre, montant, mois, aujourdhui())
    v = Versement.objects.create(
        membre=membre,
        paroisse=affectation.paroisse,
        montant=montant,
        date_versement=date_versement,
        saisi_par=par,
    )
    try:
        with transaction.atomic():
            MoisCotise.objects.bulk_create(
                MoisCotise(versement=v, membre=membre, mois=m, montant=prix) for m, prix in couverts
            )
    except IntegrityError as e:
        raise CotisationRefusee("Un de ces mois vient d'être enregistré par ailleurs.") from e
    _journal(
        par,
        "versement_saisi",
        unite=_cle_paroisse(affectation.paroisse),
        membre=membre.matricule,
        montant=montant,
        mois=[m.isoformat() for m, _p in couverts],
    )
    return v


def _verrouiller(membre) -> Membre:
    return Membre.objects.select_for_update(of=("self",)).get(pk=membre.pk)


def saisir_versement(
    membre, *, montant: int, date_versement: datetime.date, par, mois: list | None = None
) -> Versement:
    from apps.bureaux.perimetre import Unite

    with transaction.atomic():
        m = _verrouiller(membre)
        v = _saisir(m, montant, date_versement, par, mois)
        _notifier_unite(
            Unite("circuit", v.paroisse.circuit),
            f"Cotisation à valider : {v.montant} F de {m.nom_complet} ({v.paroisse.nom}).",
        )
    return v


def saisir_collecte(
    paroisse, *, coches: dict, date_versement: datetime.date, par
) -> list[Versement]:
    """Collecte de la paroisse : tout ou rien (une erreur sur un membre annule tout)."""
    from apps.bureaux.perimetre import Unite

    liste = tarifs()
    faits, erreurs = [], []
    with transaction.atomic():
        for pk in sorted(coches):
            mois = [premier_du_mois(m) for m in coches[pk] if m]
            if not mois:
                continue
            membre = _verrouiller(Membre(pk=pk))
            a = membre.affectation_actuelle
            if a is None or a.paroisse_id != paroisse.pk:
                erreurs.append(f"{membre.nom_complet} : n'est pas membre de cette paroisse.")
                continue
            montant = sum(tarif_parmi(liste, m).montant for m in mois)
            try:
                faits.append(_saisir(membre, montant, date_versement, par, mois))
            except CotisationRefusee as e:
                erreurs.append(f"{membre.nom_complet} : {e}")
        if erreurs:
            transaction.set_rollback(True)
            raise CotisationRefusee("Rien n'a été enregistré. " + " ; ".join(erreurs))
        if not faits:
            raise CotisationRefusee("Aucun mois coché.")
        total = sum(v.montant for v in faits)
        _notifier_unite(
            Unite("circuit", paroisse.circuit),
            f"Cotisations à valider : {len(faits)} versement(s), {total} F ({paroisse.nom}).",
        )
    return faits


def _parts(versement, liste) -> dict[str, int]:
    """Parts en F CFA ; l'arrondi va à la paroisse, le total est toujours exact."""
    parts = {"paroisse": 0, "circuit": 0, "region": 0, "national": 0}
    for mc in versement.mois.filter(actif=True):
        pourcentages = tarif_parmi(liste, mc.mois).parts
        for niveau in ("circuit", "region", "national"):
            parts[niveau] += mc.montant * pourcentages[niveau] // 100
    parts["paroisse"] = versement.montant - sum(parts.values())
    return parts


def _numero_recu(jour: datetime.date) -> str:
    ParametresCotisations.objects.select_for_update().get(pk=ParametresCotisations.courant().pk)
    prefixe = f"R{jour.year}-"
    dernier = (
        Versement.objects.filter(numero_recu__startswith=prefixe)
        .order_by("-numero_recu")
        .values_list("numero_recu", flat=True)
        .first()
    )
    n = int(dernier.removeprefix(prefixe)) + 1 if dernier else 1
    return f"{prefixe}{n:06d}"


def valider(versements, *, par) -> list[Versement]:
    from apps.notifications.services import notifier

    liste = tarifs()
    faits = []
    with transaction.atomic():
        for v in sorted(versements, key=lambda x: x.pk):
            v = Versement.objects.select_for_update().select_related("membre").get(pk=v.pk)
            if v.etat != EtatVersement.EN_ATTENTE:
                raise CotisationRefusee(
                    f"Le versement de {v.membre.nom_complet} n'est plus en attente."
                )
            maintenant = timezone.now()
            v.etat, v.valide_par, v.date_validation = EtatVersement.VALIDE, par, maintenant
            v.numero_recu = _numero_recu(timezone.localdate(maintenant))
            v.parts = _parts(v, liste)
            v.save()
            mois = list(v.mois.values_list("mois", flat=True))
            _journal(
                par,
                "versement_valide",
                unite=f"circuit-{v.paroisse.circuit_id}",
                membre=v.membre.matricule,
                montant=v.montant,
                recu=v.numero_recu,
            )
            compte, texte = (
                v.membre.compte,
                (
                    f"Votre cotisation de {v.montant} F ({periode(mois)}) est validée "
                    f"(reçu {v.numero_recu})."
                ),
            )
            transaction.on_commit(lambda c=compte, t=texte: notifier([c], t))
            faits.append(v)
    return faits


def _liberer(v):
    MoisCotise.objects.filter(versement=v).update(actif=False)


def refuser(versement, *, motif: str, par) -> Versement:
    from apps.bureaux.perimetre import Unite

    motif = (motif or "").strip()
    if not motif:
        raise CotisationRefusee("Le motif du refus est obligatoire.")
    with transaction.atomic():
        v = Versement.objects.select_for_update().select_related("membre").get(pk=versement.pk)
        if v.etat != EtatVersement.EN_ATTENTE:
            raise CotisationRefusee("Ce versement n'est plus en attente.")
        v.etat, v.motif, v.valide_par, v.date_validation = (
            EtatVersement.REFUSE,
            motif,
            par,
            timezone.now(),
        )
        v.save()
        _liberer(v)
        _journal(
            par,
            "versement_refuse",
            unite=f"circuit-{v.paroisse.circuit_id}",
            membre=v.membre.matricule,
            montant=v.montant,
            motif=motif,
        )
        _notifier_unite(
            Unite("paroisse", v.paroisse),
            f"Versement refusé par le circuit : {v.montant} F de {v.membre.nom_complet} "
            f"(motif : {motif}).",
        )
    return v


def annuler(versement, *, motif: str, par) -> Versement:
    motif = (motif or "").strip()
    if not motif:
        raise CotisationRefusee("Le motif de l'annulation est obligatoire.")
    with transaction.atomic():
        v = Versement.objects.select_for_update().select_related("membre").get(pk=versement.pk)
        if v.etat not in (EtatVersement.EN_ATTENTE, EtatVersement.VALIDE):
            raise CotisationRefusee("Ce versement est déjà refusé ou annulé.")
        v.etat, v.motif = EtatVersement.ANNULE, motif
        v.save()
        _liberer(v)
        _journal(
            par,
            "versement_annule",
            unite=_cle_paroisse(v.paroisse),
            membre=v.membre.matricule,
            montant=v.montant,
            motif=motif,
        )
    return v


def part_due(niveau: str, paroisse, mois_validation: datetime.date) -> int:
    debut = premier_du_mois(mois_validation)
    fin = mois_suivant(debut)
    total = 0
    for parts in Versement.objects.filter(
        paroisse=paroisse,
        etat=EtatVersement.VALIDE,
        date_validation__date__gte=debut,
        date_validation__date__lt=fin,
    ).values_list("parts", flat=True):
        total += int(parts.get(niveau, 0))
    return total


def marquer_part_recue(*, niveau: str, paroisse, mois_validation: datetime.date, par) -> PartRecue:
    mois_validation = premier_du_mois(mois_validation)
    montant = part_due(niveau, paroisse, mois_validation)
    if not montant:
        raise CotisationRefusee("Aucune part à recevoir pour cette paroisse et ce mois.")
    try:
        with transaction.atomic():
            p = PartRecue.objects.create(
                niveau=niveau,
                paroisse=paroisse,
                mois_validation=mois_validation,
                montant=montant,
                marquee_par=par,
            )
    except IntegrityError as e:
        raise CotisationRefusee("Cette part est déjà marquée comme reçue.") from e
    _journal(
        par,
        "part_recue",
        niveau=niveau,
        paroisse=paroisse.nom,
        mois=mois_validation.isoformat(),
        montant=montant,
    )
    return p


def regler(*, par, mois_depart: datetime.date | None = None, tarif: dict | None = None) -> None:
    """Réglages du BNC : mois de départ, nouveau tarif (montant et répartition)."""
    with transaction.atomic():
        if mois_depart is not None:
            p = ParametresCotisations.courant()
            p.mois_depart = premier_du_mois(mois_depart)
            p.save()
        if tarif is not None:
            t = Tarif(**{**tarif, "date_effet": premier_du_mois(tarif["date_effet"])})
            try:
                t.full_clean()
            except ValidationError as e:
                raise CotisationRefusee(" ".join(e.messages)) from e
            t.save()
        _journal(
            par,
            "reglage_cotisations",
            unite="national",
            mois_depart=mois_depart.isoformat() if mois_depart else None,
            tarif={k: str(v) for k, v in tarif.items()} if tarif else None,
        )


def rappeler_en_attente(jour: datetime.date) -> int:
    """Rappel aux circuits : versements en attente depuis plus de 30 jours. Rend leur nombre."""
    from apps.bureaux.perimetre import Unite

    limite = timezone.make_aware(
        datetime.datetime.combine(
            jour - datetime.timedelta(days=DELAI_RAPPEL_JOURS), datetime.time()
        )
    )
    par_circuit: dict = {}
    for v in Versement.objects.filter(
        etat=EtatVersement.EN_ATTENTE, date_saisie__lt=limite
    ).select_related("paroisse__circuit"):
        par_circuit.setdefault(v.paroisse.circuit, []).append(v)
    for circuit, liste in par_circuit.items():
        _notifier_unite(
            Unite("circuit", circuit),
            f"Rappel : {len(liste)} versement(s) de cotisation attendent votre validation depuis "
            f"plus de {DELAI_RAPPEL_JOURS} jours.",
        )
    return sum(len(x) for x in par_circuit.values())


__all__ = [
    "CotisationRefusee",
    "NiveauPart",
    "annuler",
    "marquer_part_recue",
    "periode",
    "rappeler_en_attente",
    "refuser",
    "regler",
    "saisir_collecte",
    "saisir_versement",
    "valider",
]
