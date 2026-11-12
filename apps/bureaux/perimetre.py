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
