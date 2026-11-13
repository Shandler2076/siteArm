"""Le gardien des périmètres : le SEUL endroit qui décide qui voit quels membres.

Toute vue qui affiche des membres passe par ces fonctions. Les filtres sont faits en base.
"""

import datetime
from dataclasses import dataclass

from django.db.models import Q, QuerySet
from django.http import Http404

from apps.bureaux.models import Mandat, Niveau
from apps.comptes.models import Compte
from apps.membres.models import Affectation, Membre, Statut
from apps.organisation.models import Circuit, Paroisse, Region

MODELES = {Niveau.PAROISSE: Paroisse, Niveau.CIRCUIT: Circuit, Niveau.REGION: Region}
ORDRE = {Niveau.NATIONAL: 0, Niveau.REGION: 1, Niveau.CIRCUIT: 2, Niveau.PAROISSE: 3}
LIBELLES = {Niveau.PAROISSE: "Paroisse", Niveau.CIRCUIT: "Circuit", Niveau.REGION: "Région"}


@dataclass(frozen=True)
class Unite:
    niveau: str
    objet: Paroisse | Circuit | Region | None

    @property
    def cle(self) -> str:
        return "national" if self.niveau == Niveau.NATIONAL else f"{self.niveau}-{self.objet.pk}"

    @property
    def libelle(self) -> str:
        if self.niveau == Niveau.NATIONAL:
            return "Bureau National de Commandement"
        prefixe = LIBELLES[self.niveau]
        if self.objet.nom.lower().startswith(prefixe.lower()):
            return self.objet.nom  # « Paroisse Saint Michel… » : pas de « Paroisse » en double
        return f"{prefixe} {self.objet.nom}"


def _mandats_de_gestion(jour: datetime.date | None = None):
    return Mandat.objects.en_cours(jour).filter(
        fonction__droit_gerer=True, membre__statut=Statut.ACTIF
    )


def unites_gerees(compte, jour: datetime.date | None = None) -> list[Unite]:
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return []
    mandats = (
        _mandats_de_gestion(jour)
        .filter(membre__compte=compte)
        .select_related("fonction", "paroisse", "circuit", "region")
    )
    unites = {Unite(m.fonction.niveau, m.unite) for m in mandats}
    return sorted(unites, key=lambda u: (ORDRE[u.niveau], u.objet.nom if u.objet else ""))


def est_bn(compte, jour: datetime.date | None = None) -> bool:
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return False
    if compte.is_superuser:
        return True
    return (
        _mandats_de_gestion(jour)
        .filter(membre__compte=compte, fonction__niveau=Niveau.NATIONAL)
        .exists()
    )


def unite_depuis_cle(compte, cle: str) -> Unite:
    if cle == "national":
        unite = Unite(Niveau.NATIONAL, None)
    else:
        niveau, _, ident = cle.partition("-")
        if niveau not in MODELES or not ident.isdigit():
            raise Http404
        objet = MODELES[niveau].objects.filter(pk=int(ident)).first()
        if objet is None:
            raise Http404
        unite = Unite(niveau, objet)
    if est_bn(compte) or unite in unites_gerees(compte):
        return unite
    raise Http404


def _filtre_affectation(unite: Unite, prefixe: str) -> dict:
    if unite.niveau == Niveau.PAROISSE:
        return {f"{prefixe}paroisse": unite.objet}
    if unite.niveau == Niveau.CIRCUIT:
        return {f"{prefixe}paroisse__circuit": unite.objet}
    return {f"{prefixe}paroisse__circuit__region": unite.objet}


def _mandats_cotisations(jour: datetime.date | None = None):
    """Gestion OU trésorerie : les trésoriers encaissent les cotisations (décision du 12/11/2026)
    sans avoir le droit de gérer le reste du site."""
    return Mandat.objects.en_cours(jour).filter(
        Q(fonction__droit_gerer=True) | Q(fonction__nom__startswith="Trésorier"),
        membre__statut=Statut.ACTIF,
    )


def unites_cotisations(compte, jour: datetime.date | None = None) -> list[Unite]:
    """Unités dont le compte voit et gère les cotisations (gestion ou trésorier ; BN = national)."""
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return []
    mandats = (
        _mandats_cotisations(jour)
        .filter(membre__compte=compte)
        .select_related("fonction", "paroisse", "circuit", "region")
    )
    unites = {Unite(m.fonction.niveau, m.unite) for m in mandats}
    if compte.is_superuser:
        unites.add(Unite(Niveau.NATIONAL, None))
    return sorted(unites, key=lambda u: (ORDRE[u.niveau], u.objet.nom if u.objet else ""))


def unite_cotisations_depuis_cle(compte, cle: str) -> Unite:
    """Comme `unite_depuis_cle`, pour les pages des cotisations (404 si pas le droit)."""
    if cle == "national":
        unite = Unite(Niveau.NATIONAL, None)
    else:
        niveau, _, ident = cle.partition("-")
        if niveau not in MODELES or not ident.isdigit():
            raise Http404
        objet = MODELES[niveau].objects.filter(pk=int(ident)).first()
        if objet is None:
            raise Http404
        unite = Unite(niveau, objet)
    if unite in unites_cotisations(compte):
        return unite
    raise Http404


def peut_voir_cotisations_de(compte, membre: Membre) -> bool:
    """Le membre lui-même, ou un bureau (gestion ou trésorier) dont le périmètre le contient."""
    if membre.compte_id and membre.compte_id == getattr(compte, "pk", None):
        return True
    return any(
        membres_visibles(u).filter(pk=membre.pk).exists() for u in unites_cotisations(compte)
    )


def peut_imprimer_autorisation(compte, convocation) -> bool:
    """Autorisation d'un événement : le membre lui-même, le Bureau national, ou le bureau de la
    paroisse actuelle du membre (décision du 12/11/2026) — jamais le circuit ni la région."""
    membre = convocation.membre
    if membre.compte_id and membre.compte_id == getattr(compte, "pk", None):
        return True
    if getattr(compte, "is_authenticated", False) and (
        compte.has_perm("membres.gerer_membres") or est_bn(compte)
    ):
        return True
    a = membre.affectation_actuelle
    return a is not None and Unite(Niveau.PAROISSE, a.paroisse) in unites_gerees(compte)


def secretaires(unite: Unite, jour: datetime.date | None = None) -> QuerySet[Compte]:
    """Comptes des Secrétaires (en fonction) de l'unité : Secrétaire de Circuit, régional…"""
    mandats = Mandat.objects.en_cours(jour).filter(
        fonction__niveau=unite.niveau,
        fonction__nom__startswith="Secrétaire",
        membre__statut=Statut.ACTIF,
    )
    if unite.objet is not None:
        mandats = mandats.filter(**{unite.niveau: unite.objet})
    return Compte.objects.filter(is_active=True, membre__in=mandats.values("membre")).distinct()


# « Vérifier un membre » : Chef et Secrétaire des bureaux de paroisse, circuit et région.
FONCTIONS_CHEF = ("Chef d'Unité paroissiale", "Chef de Section de Circuit", "Coordinateur régional")
FONCTIONS_VERIFICATION = (
    *FONCTIONS_CHEF,
    "Secrétaire paroissial",
    "Secrétaire de Circuit",
    "Secrétaire régional",
)


def unites_verification(compte, jour: datetime.date | None = None) -> list[Unite]:
    """Bureaux d'où le compte peut vérifier l'identité d'un membre hors de son périmètre."""
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return []
    mandats = (
        Mandat.objects.en_cours(jour)
        .filter(
            membre__compte=compte,
            membre__statut=Statut.ACTIF,
            fonction__nom__in=FONCTIONS_VERIFICATION,
        )
        .exclude(fonction__niveau=Niveau.NATIONAL)
        .select_related("fonction", "paroisse", "circuit", "region")
    )
    unites = {Unite(m.fonction.niveau, m.unite) for m in mandats}
    return sorted(unites, key=lambda u: (ORDRE[u.niveau], u.objet.nom if u.objet else ""))


def titulaires_cotisations(unite: Unite, jour: datetime.date | None = None) -> QuerySet[Compte]:
    mandats = _mandats_cotisations(jour).filter(fonction__niveau=unite.niveau)
    if unite.objet is not None:
        mandats = mandats.filter(**{unite.niveau: unite.objet})
    return Compte.objects.filter(is_active=True, membre__in=mandats.values("membre")).distinct()


def membres_visibles(unite: Unite) -> QuerySet[Membre]:
    if unite.niveau == Niveau.NATIONAL:
        return Membre.objects.all()
    return Membre.objects.filter(
        affectations__date_fin__isnull=True, **_filtre_affectation(unite, "affectations__")
    ).distinct()


def peut_voir_membre(compte, membre: Membre) -> bool:
    if membre.compte_id and membre.compte_id == getattr(compte, "pk", None):
        return True
    if est_bn(compte):
        return True
    return any(membres_visibles(u).filter(pk=membre.pk).exists() for u in unites_gerees(compte))


def anciens_membres(unite: Unite) -> QuerySet[Affectation]:
    if unite.niveau == Niveau.NATIONAL:
        return Affectation.objects.none()
    champ = {
        Niveau.PAROISSE: "paroisse",
        Niveau.CIRCUIT: "circuit_a_date",
        Niveau.REGION: "region_a_date",
    }[unite.niveau]
    return (
        Affectation.objects.filter(date_fin__isnull=False, **{champ: unite.objet})
        .exclude(membre__in=membres_visibles(unite))
        .select_related("membre")
        .order_by("-date_fin")
    )


def titulaires_gestion(unite: Unite, jour: datetime.date | None = None) -> QuerySet[Compte]:
    mandats = _mandats_de_gestion(jour).filter(fonction__niveau=unite.niveau)
    if unite.objet is not None:
        mandats = mandats.filter(**{unite.niveau: unite.objet})
    return Compte.objects.filter(is_active=True, membre__in=mandats.values("membre")).distinct()


def membre_pour_mutation(matricule: str) -> Membre | None:
    """Seule exception au périmètre : la paroisse d'arrivée retrouve un membre par matricule.

    La vue n'en affiche que le nom, les prénoms et la paroisse actuelle (confirmation).
    """
    return (
        Membre.objects.filter(matricule=(matricule or "").strip().upper())
        .prefetch_related("affectations__paroisse")
        .first()
    )


# --- Trésorerie (décisions du mainteneur du 13/11/2026) ------------------------------------------
TRESORIERS_LOCAUX = {
    Niveau.PAROISSE: "Trésorier paroissial",
    Niveau.CIRCUIT: "Trésorier de Circuit",
    Niveau.REGION: "Trésorier régional",
}
SECRETAIRES_LOCAUX = ("Secrétaire paroissial", "Secrétaire de Circuit", "Secrétaire régional")


def _mandats_unite(unite: Unite, noms, jour=None):
    mandats = Mandat.objects.en_cours(jour).filter(
        fonction__niveau=unite.niveau, fonction__nom__in=noms, membre__statut=Statut.ACTIF
    )
    if unite.objet is not None:
        mandats = mandats.filter(**{unite.niveau: unite.objet})
    return mandats


def tresoriers(unite: Unite, jour: datetime.date | None = None) -> QuerySet[Compte]:
    """Comptes qui tiennent la trésorerie de l'unité : le Trésorier, ou le Chef si le poste est
    vacant (intérim)."""
    noms = [TRESORIERS_LOCAUX.get(unite.niveau, "Trésorier national")]
    mandats = _mandats_unite(unite, noms, jour)
    if not mandats.exists():
        mandats = _mandats_unite(unite, FONCTIONS_CHEF, jour)
    return Compte.objects.filter(is_active=True, membre__in=mandats.values("membre")).distinct()


def unites_tresorerie(compte, jour: datetime.date | None = None) -> list[tuple[Unite, bool]]:
    """[(unité, peut_agir)] : le Trésorier (ou le Chef par intérim) agit ; le Chef et le
    Secrétaire voient en lecture seule. Niveaux paroisse, circuit et région."""
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return []
    noms = (*TRESORIERS_LOCAUX.values(), *FONCTIONS_CHEF, *SECRETAIRES_LOCAUX)
    mandats = (
        Mandat.objects.en_cours(jour)
        .filter(membre__compte=compte, membre__statut=Statut.ACTIF, fonction__nom__in=noms)
        .exclude(fonction__niveau=Niveau.NATIONAL)
        .select_related("fonction", "paroisse", "circuit", "region")
    )
    resultat: dict[Unite, bool] = {}
    for m in mandats:
        unite = Unite(m.fonction.niveau, m.unite)
        agit = tresoriers(unite, jour).filter(pk=compte.pk).exists()
        resultat[unite] = resultat.get(unite, False) or agit
    return sorted(
        resultat.items(), key=lambda p: (ORDRE[p[0].niveau], p[0].objet.nom if p[0].objet else "")
    )


def peut_agir_tresorerie(compte, unite: Unite) -> bool:
    return any(u == unite and agit for u, agit in unites_tresorerie(compte))


def peut_voir_tresorerie(compte, unite: Unite) -> bool:
    return any(u == unite for u, _agit in unites_tresorerie(compte))


def _a_fonction_nationale(compte, noms) -> bool:
    if not getattr(compte, "is_authenticated", False) or not compte.is_active:
        return False
    if compte.is_superuser:
        return True
    return (
        Mandat.objects.en_cours()
        .filter(
            membre__compte=compte,
            membre__statut=Statut.ACTIF,
            fonction__niveau=Niveau.NATIONAL,
            fonction__nom__in=noms,
        )
        .exists()
    )


def est_tresorier_national(compte) -> bool:
    """Prépare l'état des reversements et enregistre les envois."""
    return _a_fonction_nationale(compte, ("Trésorier national", "Trésorier national adjoint"))


def est_validateur_reversements(compte) -> bool:
    """Valide l'état mensuel des reversements : le Président ou le Secrétaire national."""
    return _a_fonction_nationale(compte, ("Président", "Secrétaire national"))
