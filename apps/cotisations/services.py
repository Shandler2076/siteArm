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
    ModeVersement,
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
from apps.cotisations.regles import HORS_MOUVEMENT, mois_suivant, situation
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


def _notifier_unite(unite, message, lien=""):
    from apps.bureaux.perimetre import titulaires_cotisations
    from apps.notifications.services import notifier

    transaction.on_commit(lambda: notifier(titulaires_cotisations(unite), message, lien))


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
    # Paiement d'avance (mois après le mois en cours) : seulement pour un membre encore dans le
    # mouvement. Mois passés ou en cours : seulement les mois dus (pas pendant une exclusion…).
    avance_permise = membre.statut not in HORS_MOUVEMENT
    if mois_choisis:
        choisis = sorted({premier_du_mois(m) for m in mois_choisis})
        for m in choisis:
            hors = (m <= courant and m not in s.dus) or (m > courant and not avance_permise)
            if m < debut or m > fin_annee or hors:
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
    candidats = _candidats(s, courant, fin_annee, occupes, avance_permise)
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


def _candidats(s, courant, fin_annee, occupes, avance_permise) -> list[datetime.date]:
    """Mois payables dans l'ordre : les mois dus non payés, puis l'avance jusqu'en décembre."""
    candidats = [m for m in s.dus if m not in occupes]
    m = mois_suivant(courant) if avance_permise else mois_suivant(fin_annee)
    while m <= fin_annee:  # paiement d'avance : mois suivants de l'année en cours
        if m not in occupes:
            candidats.append(m)
        m = mois_suivant(m)
    return candidats


def prochains_mois(membre, nombre: int, jour: datetime.date | None = None):
    """[(mois, prix)] des `nombre` plus anciens mois payables du membre (paiement mobile money).

    Lève CotisationRefusee si les cotisations ne sont pas ouvertes ou s'il n'y a pas assez de
    mois payables jusqu'en décembre."""
    if ParametresCotisations.courant().mois_depart is None:
        raise CotisationRefusee(
            "Les cotisations ne sont pas encore ouvertes : le BNC doit fixer le mois de départ."
        )
    if nombre is None or nombre < 1:
        raise CotisationRefusee("Choisissez au moins un mois.")
    courant = premier_du_mois(jour or aujourdhui())
    s = situation(membre, courant)
    occupes = s.payes | s.en_attente
    candidats = _candidats(
        s, courant, courant.replace(month=12), occupes, membre.statut not in HORS_MOUVEMENT
    )
    if len(candidats) < nombre:
        raise CotisationRefusee(
            f"Seulement {len(candidats)} mois payable(s) jusqu'en décembre pour ce membre."
        )
    liste = tarifs()
    return [(m, tarif_parmi(liste, m).montant) for m in candidats[:nombre]]


def enregistrer_mobile_money(membre, *, mois: list, reference: str, par) -> Versement:
    """Paiement mobile money confirmé par la plateforme : versement VALIDÉ d'office (chemin unique
    décidé le 13/11/2026 : personne ne valide), reçu, parts calculées pour les reversements."""
    from apps.notifications.services import notifier

    with transaction.atomic():
        ParametresCotisations.objects.select_for_update().get(pk=ParametresCotisations.courant().pk)
        m = _verrouiller(membre)
        affectation = m.affectation_actuelle
        if affectation is None:
            raise CotisationRefusee(f"{m.nom_complet} n'est rattaché à aucune paroisse.")
        liste = tarifs()
        mois = sorted({premier_du_mois(x) for x in mois})
        montant = sum(tarif_parmi(liste, x).montant for x in mois)
        couverts = _choisir_mois(m, montant, mois, aujourdhui())
        maintenant = timezone.now()
        v = Versement.objects.create(
            membre=m,
            paroisse=affectation.paroisse,
            montant=montant,
            date_versement=timezone.localdate(maintenant),
            etat=EtatVersement.VALIDE,
            saisi_par=par,
            date_validation=maintenant,
            mode=ModeVersement.MOBILE_MONEY,
            reference_paiement=reference,
        )
        try:
            with transaction.atomic():
                MoisCotise.objects.bulk_create(
                    MoisCotise(versement=v, membre=m, mois=x, montant=prix) for x, prix in couverts
                )
        except IntegrityError as e:
            raise CotisationRefusee("Un de ces mois vient d'être payé par ailleurs.") from e
        v.numero_recu = _numero_recu(timezone.localdate(maintenant))
        v.parts = _parts(v, liste)
        v.save(update_fields=["numero_recu", "parts"])
        _journal(
            par,
            "versement_mobile_money",
            unite=_cle_paroisse(affectation.paroisse),
            membre=m.matricule,
            montant=montant,
            recu=v.numero_recu,
            reference=reference,
        )
        texte = (
            f"Votre cotisation de {montant} F ({periode(mois)}) est payée par mobile money "
            f"(reçu {v.numero_recu})."
        )
        transaction.on_commit(lambda: notifier([m.compte], texte, "/cotisations/moi/"))
    return v


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
            f"/cotisations/circuit-{v.paroisse.circuit_id}/a-valider/",
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
            f"/cotisations/circuit-{paroisse.circuit_id}/a-valider/",
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
    """À appeler sous le verrou de `ParametresCotisations` (pris par `valider`)."""
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
        # Verrou unique pris d'abord (numéros de reçu), puis les versements par pk : pas
        # d'interblocage entre deux validations simultanées.
        ParametresCotisations.objects.select_for_update().get(pk=ParametresCotisations.courant().pk)
        for v in sorted(versements, key=lambda x: x.pk):
            v = (
                Versement.objects.select_for_update(of=("self",))
                .select_related("membre", "paroisse")
                .get(pk=v.pk)
            )
            if v.etat != EtatVersement.EN_ATTENTE:
                raise CotisationRefusee(
                    f"Le versement de {v.membre.nom_complet} n'est plus en attente."
                )
            if par is not None and v.saisi_par_id == getattr(par, "pk", None):
                raise CotisationRefusee(
                    f"Vous avez saisi le versement de {v.membre.nom_complet} : un autre membre "
                    "du bureau du circuit doit le valider."
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
            transaction.on_commit(lambda c=compte, t=texte: notifier([c], t, "/cotisations/moi/"))
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
        v = (
            Versement.objects.select_for_update(of=("self",))
            .select_related("membre", "paroisse")
            .get(pk=versement.pk)
        )
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
            f"/cotisations/paroisse-{v.paroisse_id}/",
        )
    return v


def annuler(versement, *, motif: str, par) -> Versement:
    motif = (motif or "").strip()
    if not motif:
        raise CotisationRefusee("Le motif de l'annulation est obligatoire.")
    with transaction.atomic():
        v = (
            Versement.objects.select_for_update(of=("self",))
            .select_related("membre", "paroisse")
            .get(pk=versement.pk)
        )
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


def marquer_part_recue(
    *,
    niveau: str,
    paroisse,
    mois_validation: datetime.date,
    par,
    aujourd_hui: datetime.date | None = None,
) -> PartRecue:
    mois_validation = premier_du_mois(mois_validation)
    if mois_validation >= premier_du_mois(aujourd_hui or timezone.localdate()):
        raise CotisationRefusee(
            "La part se marque comme reçue une fois le mois terminé (d'autres versements "
            "peuvent encore être validés ce mois-ci)."
        )
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
        unite={
            "circuit": f"circuit-{paroisse.circuit_id}",
            "region": f"region-{paroisse.circuit.region_id}",
        }.get(niveau, "national"),
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


JOUR_DU_RAPPEL = 5  # samedi (lundi = 0)


def rappeler_en_attente(jour: datetime.date, forcer: bool = False) -> int:
    """Rappel hebdomadaire (le samedi) : versements en attente depuis plus de 30 jours.

    Il part au Secrétaire de circuit (sur le site et par e-mail s'il en a un) ; à défaut, aux
    autres responsables du circuit. Rend le nombre de versements concernés.
    """
    from apps.bureaux.perimetre import Unite, secretaires, titulaires_cotisations
    from apps.notifications.services import notifier

    if jour.weekday() != JOUR_DU_RAPPEL and not forcer:
        return 0
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
        unite = Unite("circuit", circuit)
        destinataires = list(secretaires(unite)) or list(titulaires_cotisations(unite))
        texte = (
            f"Rappel du samedi : {len(liste)} versement(s) de cotisation attendent votre "
            f"validation depuis plus de {DELAI_RAPPEL_JOURS} jours ({unite.libelle})."
        )
        lien = f"/cotisations/{unite.cle}/a-valider/"
        transaction.on_commit(lambda d=destinataires, t=texte, x=lien: notifier(d, t, x))
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
