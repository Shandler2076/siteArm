"""SEUL point d'écriture de la trésorerie (décisions du mainteneur du 13/11/2026).

- Paiement mobile money : il part toujours du site ; la plateforme (ici simulée) confirme ; le site
  enregistre alors exactement ce qui a été payé (mois, membres, cotisation spéciale).
- Cotisations mensuelles payées par mobile money : validées d'office (personne ne valide) ; leurs
  parts sont reversées chaque mois par le BN (préparation par le Trésorier national, validation par
  le Président ou le Secrétaire national, envoi enregistré par le Trésorier national).
- Cotisations spéciales : payées à 100 % au BN, en une ou plusieurs fois, quittance à chaque fois.
"""

import datetime
import secrets

from django.db import transaction
from django.db.models import Sum
from django.http import QueryDict
from django.utils import timezone

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import MODELES, Unite
from apps.membres.models import Membre, Statut
from apps.tresorerie.models import (  # noqa: F401 — NumeroMobileMoney sert aussi à la démo
    Contribution,
    CotisationSpeciale,
    EtatPaiement,
    EtatReversement,
    NaturePaiement,
    NumeroMobileMoney,
    Paiement,
    PourMembres,
    Reversement,
    TypeMontant,
)

NATIONAL = Unite(Niveau.NATIONAL, None)
NIVEAUX_BUREAUX = [
    (Niveau.PAROISSE, "Bureaux de paroisse"),
    (Niveau.CIRCUIT, "Bureaux de circuit"),
    (Niveau.REGION, "Bureaux de région"),
]


class TresorerieRefusee(Exception):
    """Opération refusée ; le message s'affiche tel quel."""


def _journal(par, action, unite="national", **details):
    from apps.journal.services import journaliser

    journaliser(par, action, unite=unite, **details)


def unite_par_cle(cle: str) -> Unite | None:
    """Unité désignée par sa clé (« paroisse-3 »…), sans contrôle de droits."""
    if cle == "national":
        return NATIONAL
    niveau, _, ident = (cle or "").partition("-")
    if niveau not in MODELES or not ident.isdigit():
        return None
    objet = MODELES[niveau].objects.filter(pk=int(ident)).first()
    return Unite(niveau, objet) if objet else None


# --- Numéros mobile money des bureaux (BN seulement) ---------------------------------------------


def enregistrer_numero(unite: Unite, *, numero: str, titulaire: str = "", par) -> NumeroMobileMoney:
    numero = "".join(c for c in (numero or "") if c.isdigit() or c == "+")
    if len(numero.lstrip("+")) < 8:
        raise TresorerieRefusee("Numéro mobile money invalide (au moins 8 chiffres).")
    n, _ = NumeroMobileMoney.objects.update_or_create(
        cle=unite.cle,
        defaults={
            "libelle": unite.libelle,
            "numero": numero,
            "titulaire": (titulaire or "").strip()[:200],
            "modifie_par": par,
        },
    )
    _journal(par, "numero_tresorier", unite_libelle=unite.libelle, cle=unite.cle)
    return n


def numero_de(cle: str) -> str:
    n = NumeroMobileMoney.objects.filter(cle=cle).first()
    return n.numero if n else ""


# --- Cotisations spéciales -----------------------------------------------------------------------


def creer_cotisation_speciale(
    *,
    libelle: str,
    par,
    description: str = "",
    echeance: datetime.date | None = None,
    type_montant: str = TypeMontant.FIXE,
    montant: int | None = None,
    pour_membres: str = PourMembres.TOUS,
    criteres: dict | None = None,
    pour_bureaux: list[str] | None = None,
) -> CotisationSpeciale:
    libelle = (libelle or "").strip()
    if not libelle:
        raise TresorerieRefusee("Le libellé est obligatoire.")
    if type_montant not in TypeMontant.values or pour_membres not in PourMembres.values:
        raise TresorerieRefusee("Choix inconnu.")
    if type_montant == TypeMontant.LIBRE:
        montant = None
    elif not montant or montant <= 0:
        raise TresorerieRefusee("Indiquez le montant (fixe ou minimum).")
    bureaux = [n for n in (pour_bureaux or []) if n in dict(NIVEAUX_BUREAUX)]
    if pour_membres == PourMembres.AUCUN and not bureaux:
        raise TresorerieRefusee("Choisissez au moins des membres ou des bureaux concernés.")
    cs = CotisationSpeciale.objects.create(
        libelle=libelle,
        description=(description or "").strip(),
        echeance=echeance,
        type_montant=type_montant,
        montant=montant,
        pour_membres=pour_membres,
        criteres=(criteres or {}) if pour_membres == PourMembres.CERTAINS else {},
        pour_bureaux=bureaux,
        cree_par=par,
    )
    _journal(par, "cotisation_speciale", libelle=cs.libelle, cotisation=cs.pk)
    return cs


def membres_concernes(cs: CotisationSpeciale):
    """Membres à qui la cotisation est demandée (encore dans le mouvement)."""
    from apps.listes.filtres import FiltreListeForm, membres_filtres

    if cs.pour_membres == PourMembres.AUCUN:
        return Membre.objects.none()
    vivants = Membre.objects.filter(statut__in=[Statut.ACTIF, Statut.SANCTIONNE])
    if cs.pour_membres == PourMembres.TOUS:
        return vivants
    donnees = QueryDict(mutable=True)
    for cle, valeur in (cs.criteres or {}).items():
        donnees.setlist(cle, valeur if isinstance(valeur, list) else [valeur])
    donnees["envoye"] = "1"
    form = FiltreListeForm(NATIONAL, donnees)
    if not form.is_valid():
        return Membre.objects.none()
    return membres_filtres(NATIONAL, form.cleaned_data, timezone.localdate()).filter(
        pk__in=vivants.values("pk")
    )


def concerne_membre(cs: CotisationSpeciale, membre) -> bool:
    return cs.ouverte and membres_concernes(cs).filter(pk=membre.pk).exists()


def concerne_unite(cs: CotisationSpeciale, unite: Unite) -> bool:
    return cs.ouverte and unite.niveau in (cs.pour_bureaux or [])


def deja_paye(cs: CotisationSpeciale, *, membre=None, unite_cle: str = "") -> int:
    qs = cs.contributions.all()
    qs = qs.filter(membre=membre) if membre is not None else qs.filter(unite_cle=unite_cle)
    return qs.aggregate(t=Sum("montant"))["t"] or 0


def reste_a_payer(cs: CotisationSpeciale, *, membre=None, unite_cle: str = "") -> int | None:
    """Ce qu'il reste à payer (None pour un montant libre)."""
    if cs.type_montant == TypeMontant.LIBRE:
        return None
    return max(0, cs.montant - deja_paye(cs, membre=membre, unite_cle=unite_cle))


def est_reglee(cs: CotisationSpeciale, *, membre=None, unite_cle: str = "") -> bool:
    paye = deja_paye(cs, membre=membre, unite_cle=unite_cle)
    if cs.type_montant == TypeMontant.LIBRE:
        return paye > 0
    return paye >= cs.montant


def speciales_du_membre(membre) -> list[dict]:
    lignes = []
    for cs in CotisationSpeciale.objects.filter(ouverte=True):
        if concerne_membre(cs, membre):
            lignes.append(
                {
                    "cs": cs,
                    "paye": deja_paye(cs, membre=membre),
                    "reste": reste_a_payer(cs, membre=membre),
                    "reglee": est_reglee(cs, membre=membre),
                }
            )
    return lignes


def speciales_du_bureau(unite: Unite) -> list[dict]:
    lignes = []
    for cs in CotisationSpeciale.objects.filter(ouverte=True):
        if concerne_unite(cs, unite):
            lignes.append(
                {
                    "cs": cs,
                    "paye": deja_paye(cs, unite_cle=unite.cle),
                    "reste": reste_a_payer(cs, unite_cle=unite.cle),
                    "reglee": est_reglee(cs, unite_cle=unite.cle),
                }
            )
    return lignes


# --- Paiements (le paiement part toujours du site) ------------------------------------------------


def _reference() -> str:
    return f"AS{timezone.localtime():%y%m%d}-{secrets.token_hex(4).upper()}"


def initier_paiement_mensuel(payeur, lignes) -> Paiement:
    """`lignes` : [(membre, nombre de mois)]. Les mois payés sont les plus anciens mois dus."""
    from apps.cotisations.services import CotisationRefusee, prochains_mois

    objet, total, noms = [], 0, []
    for membre, nombre in lignes:
        if not nombre:
            continue
        try:
            mois = prochains_mois(membre, int(nombre))
        except CotisationRefusee as e:
            raise TresorerieRefusee(f"{membre.matricule} : {e}") from e
        objet.append(
            {
                "membre": membre.pk,
                "matricule": membre.matricule,
                "mois": [m.isoformat() for m, _p in mois],
            }
        )
        total += sum(p for _m, p in mois)
        noms.append(membre.matricule)
    if not objet:
        raise TresorerieRefusee("Indiquez au moins un mois à payer.")
    return Paiement.objects.create(
        reference=_reference(),
        payeur=payeur,
        nature=NaturePaiement.MENSUELLE,
        montant=total,
        objet={"lignes": objet},
        description=f"Cotisation mensuelle — {', '.join(noms)}"[:300],
    )


def initier_paiement_special(
    payeur, cs: CotisationSpeciale, montant: int, *, membre=None, unite: Unite | None = None
) -> Paiement:
    if not cs.ouverte:
        raise TresorerieRefusee("Cette cotisation spéciale est close.")
    if (membre is None) == (unite is None):
        raise TresorerieRefusee("Paiement pour un membre ou au nom d'un bureau.")
    if membre is not None and not concerne_membre(cs, membre):
        raise TresorerieRefusee("Cette cotisation spéciale ne concerne pas ce membre.")
    if unite is not None and not concerne_unite(cs, unite):
        raise TresorerieRefusee("Cette cotisation spéciale ne concerne pas ce bureau.")
    if not montant or montant <= 0:
        raise TresorerieRefusee("Le montant doit être positif.")
    cle = unite.cle if unite else ""
    reste = reste_a_payer(cs, membre=membre, unite_cle=cle)
    if cs.type_montant == TypeMontant.FIXE and montant > reste:
        raise TresorerieRefusee(f"Le montant dépasse ce qu'il reste à payer ({reste} F).")
    objet = (
        {"membre": membre.pk, "matricule": membre.matricule}
        if membre
        else {"unite": cle, "libelle": unite.libelle}
    )
    pour = membre.matricule if membre else unite.libelle
    return Paiement.objects.create(
        reference=_reference(),
        payeur=payeur,
        nature=NaturePaiement.SPECIALE,
        cotisation_speciale=cs,
        montant=montant,
        objet=objet,
        description=f"{cs.libelle} — {pour}"[:300],
    )


def _numero_quittance(jour: datetime.date) -> str:
    prefixe = f"Q{jour.year}-"
    dernier = (
        Contribution.objects.filter(quittance__startswith=prefixe)
        .order_by("-quittance")
        .values_list("quittance", flat=True)
        .first()
    )
    n = int(dernier.removeprefix(prefixe)) + 1 if dernier else 1
    return f"{prefixe}{n:06d}"


def _avertir_paroisse(membre, texte: str) -> None:
    """La paroisse du membre aidé est avertie (pour lui remettre le reçu imprimé)."""
    from apps.bureaux.perimetre import tresoriers
    from apps.notifications.services import lien_membre, notifier

    a = membre.affectation_actuelle
    if a is None:
        return
    unite = Unite(Niveau.PAROISSE, a.paroisse)
    from apps.bureaux.perimetre import titulaires_gestion

    destinataires = list(titulaires_gestion(unite)) + list(tresoriers(unite))
    notifier(destinataires, texte, lien_membre(membre))


def confirmer_paiement(paiement: Paiement) -> Paiement:
    """Confirmation de la plateforme : enregistre exactement ce qui a été payé. Idempotent."""
    from apps.cotisations.services import CotisationRefusee, enregistrer_mobile_money
    from apps.notifications.services import notifier

    with transaction.atomic():
        p = Paiement.objects.select_for_update().get(pk=paiement.pk)
        if p.etat != EtatPaiement.EN_ATTENTE:
            return p
        payeur = p.payeur
        try:
            with transaction.atomic():
                if p.nature == NaturePaiement.MENSUELLE:
                    _appliquer_mensuel(p, payeur, enregistrer_mobile_money)
                else:
                    _appliquer_special(p, payeur)
        except (CotisationRefusee, TresorerieRefusee) as e:
            p.etat, p.message = EtatPaiement.ANOMALIE, str(e)[:300]
            p.date_confirmation = timezone.now()
            p.save(update_fields=["etat", "message", "date_confirmation"])
            _journal(payeur, "paiement_echoue", reference=p.reference, motif=p.message)
            texte = (
                f"Paiement {p.reference} ({p.montant} F) reçu mais non affecté : {p.message} "
                "Le Bureau national va régulariser."
            )
            transaction.on_commit(lambda: notifier([payeur], texte))
            return p
        p.etat, p.date_confirmation = EtatPaiement.CONFIRME, timezone.now()
        p.save(update_fields=["etat", "date_confirmation"])
    return p


def _appliquer_mensuel(p, payeur, enregistrer_mobile_money):
    from apps.notifications.services import notifier

    for ligne in p.objet.get("lignes", []):
        membre = Membre.objects.get(pk=ligne["membre"])
        mois = [datetime.date.fromisoformat(m) for m in ligne["mois"]]
        v = enregistrer_mobile_money(membre, mois=mois, reference=p.reference, par=payeur)
        if membre.compte_id != payeur.pk:
            texte = (
                f"Cotisation de {membre.nom_complet} payée par mobile money par un autre membre "
                f"({v.montant} F, reçu {v.numero_recu})."
            )
            transaction.on_commit(lambda m=membre, t=texte: _avertir_paroisse(m, t))
    texte = f"Paiement confirmé : {p.montant} F ({p.description})."
    transaction.on_commit(lambda: notifier([payeur], texte, "/cotisations/moi/"))


def _appliquer_special(p, payeur):
    from apps.bureaux.perimetre import tresoriers
    from apps.notifications.services import notifier

    cs = p.cotisation_speciale
    membre = Membre.objects.filter(pk=p.objet.get("membre")).first()
    unite = unite_par_cle(p.objet.get("unite", "")) if not membre else None
    if membre is None and unite is None:
        raise TresorerieRefusee("Bénéficiaire du paiement introuvable.")
    c = Contribution.objects.create(
        cotisation=cs,
        membre=membre,
        unite_cle=unite.cle if unite else "",
        unite_libelle=unite.libelle if unite else "",
        montant=p.montant,
        quittance=_numero_quittance(timezone.localdate()),
        paiement=p,
    )
    _journal(
        payeur,
        "contribution",
        libelle=cs.libelle,
        montant=c.montant,
        quittance=c.quittance,
        membre=membre.matricule if membre else "",
        unite_libelle=c.unite_libelle,
    )
    lien = f"/tresorerie/quittance/{c.pk}.pdf"
    texte = f"« {cs.libelle} » : {c.montant} F payés (quittance {c.quittance})."
    if membre is not None:
        transaction.on_commit(lambda: notifier([membre.compte], texte, lien))
        if membre.compte_id != payeur.pk:
            transaction.on_commit(
                lambda: _avertir_paroisse(membre, f"{membre.nom_complet} — {texte}")
            )
    else:
        transaction.on_commit(lambda: notifier(list(tresoriers(unite)), texte, lien))
    if (membre is None or membre.compte_id != payeur.pk) and payeur is not None:
        transaction.on_commit(lambda: notifier([payeur], f"Paiement confirmé — {texte}", lien))


def echouer_paiement(paiement: Paiement, message: str = "Paiement annulé ou refusé.") -> Paiement:
    with transaction.atomic():
        p = Paiement.objects.select_for_update().get(pk=paiement.pk)
        if p.etat != EtatPaiement.EN_ATTENTE:
            return p
        p.etat, p.message = EtatPaiement.ECHOUE, message[:300]
        p.save(update_fields=["etat", "message"])
        _journal(p.payeur, "paiement_echoue", reference=p.reference, motif=p.message)
    return p


# --- Reversements mensuels ----------------------------------------------------------------------


def _premier(mois: datetime.date) -> datetime.date:
    return mois.replace(day=1)


def parts_du_mois(mois: datetime.date) -> dict[str, dict]:
    """Parts dues par le BN aux paroisses, circuits et régions pour les cotisations payées par
    mobile money dans le mois (date de paiement)."""
    from apps.cotisations.models import EtatVersement, ModeVersement, Versement

    mois = _premier(mois)
    suivant = (mois + datetime.timedelta(days=32)).replace(day=1)
    parts: dict[str, dict] = {}
    versements = Versement.objects.filter(
        mode=ModeVersement.MOBILE_MONEY,
        etat=EtatVersement.VALIDE,
        date_versement__gte=mois,
        date_versement__lt=suivant,
    ).select_related("paroisse__circuit__region")
    for v in versements:
        p = v.paroisse
        for niveau, objet in (
            (Niveau.PAROISSE, p),
            (Niveau.CIRCUIT, p.circuit),
            (Niveau.REGION, p.circuit.region),
        ):
            unite = Unite(niveau, objet)
            ligne = parts.setdefault(
                unite.cle, {"niveau": niveau, "libelle": unite.libelle, "montant": 0}
            )
            ligne["montant"] += int((v.parts or {}).get(niveau, 0))
    return {k: v for k, v in parts.items() if v["montant"] > 0}


def preparer_reversements(mois: datetime.date, *, par) -> list[Reversement]:
    """Trésorier national : état des reversements d'un mois terminé (refait tant que non validé)."""
    mois = _premier(mois)
    if mois >= _premier(timezone.localdate()):
        raise TresorerieRefusee("On ne prépare les reversements que d'un mois terminé.")
    faits = []
    with transaction.atomic():
        existants = {r.cle: r for r in Reversement.objects.select_for_update().filter(mois=mois)}
        for cle, ligne in parts_du_mois(mois).items():
            r = existants.get(cle)
            if r is not None and r.etat != EtatReversement.PREPARE:
                continue
            if r is None:
                r = Reversement(mois=mois, cle=cle, prepare_par=par)
            r.libelle, r.niveau, r.montant = ligne["libelle"], ligne["niveau"], ligne["montant"]
            r.numero = numero_de(cle)
            r.prepare_par = par
            r.save()
            faits.append(r)
        total = sum(r.montant for r in faits)
        _journal(par, "reversements_prepares", mois=f"{mois:%m/%Y}", total=total)
    return faits


def valider_reversements(mois: datetime.date, *, par) -> int:
    """Président ou Secrétaire national : valide l'état préparé avant les envois."""
    mois = _premier(mois)
    with transaction.atomic():
        a_valider = list(
            Reversement.objects.select_for_update().filter(mois=mois, etat=EtatReversement.PREPARE)
        )
        if not a_valider:
            raise TresorerieRefusee("Aucun reversement préparé à valider pour ce mois.")
        maintenant = timezone.now()
        for r in a_valider:
            r.etat, r.valide_par, r.date_validation = EtatReversement.VALIDE, par, maintenant
            r.save(update_fields=["etat", "valide_par", "date_validation"])
        total = sum(r.montant for r in a_valider)
        _journal(par, "reversements_valides", mois=f"{mois:%m/%Y}", total=total)
    return len(a_valider)


def marquer_envoye(reversement: Reversement, *, reference: str, par) -> Reversement:
    """Trésorier national : l'envoi mobile money au Trésorier de l'unité est fait."""
    from apps.bureaux.perimetre import tresoriers
    from apps.notifications.services import notifier

    reference = (reference or "").strip()
    if not reference:
        raise TresorerieRefusee("Indiquez la référence de l'envoi mobile money.")
    with transaction.atomic():
        r = Reversement.objects.select_for_update().get(pk=reversement.pk)
        if r.etat != EtatReversement.VALIDE:
            raise TresorerieRefusee("Ce reversement doit d'abord être validé (et non déjà envoyé).")
        if not r.numero:
            r.numero = numero_de(r.cle)
            if not r.numero:
                raise TresorerieRefusee(
                    f"Enregistrez d'abord le numéro mobile money de {r.libelle}."
                )
        r.etat, r.envoye_par, r.date_envoi = EtatReversement.ENVOYE, par, timezone.now()
        r.reference_envoi = reference[:60]
        r.save()
        _journal(
            par,
            "reversement_envoye",
            mois=f"{r.mois:%m/%Y}",
            montant=r.montant,
            unite_libelle=r.libelle,
            reference=r.reference_envoi,
        )
        unite = unite_par_cle(r.cle)
        if unite is not None:
            texte = (
                f"Reversement du Bureau national : {r.montant} F (cotisations de {r.mois:%m/%Y}) "
                f"envoyé au {r.numero}, référence {r.reference_envoi}."
            )
            lien = f"/tresorerie/{r.cle}/"
            transaction.on_commit(lambda: notifier(list(tresoriers(unite)), texte, lien))
    return r
