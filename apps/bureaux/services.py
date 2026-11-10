"""Services des bureaux : installation des bureaux, réinitialisation, échéances."""

import datetime

from django.db import transaction

from apps.bureaux.models import Fonction, Mandat
from apps.bureaux.perimetre import Unite
from apps.membres.models import Membre, Statut


class InstallationRefusee(ValueError):
    pass


def _mandats_de_l_unite(unite: Unite):
    qs = Mandat.objects.filter(fonction__niveau=unite.niveau)
    if unite.objet is not None:
        qs = qs.filter(**{unite.niveau: unite.objet})
    return qs


def installer_bureau(
    *, unite: Unite, titulaires: dict[Fonction, Membre], date_debut: datetime.date, par
) -> list[Mandat]:
    """Clôt tous les mandats en cours de l'unité et installe les nouveaux titulaires."""
    from apps.notifications.services import notifier

    if not titulaires:
        raise InstallationRefusee("Indiquez au moins un titulaire.")
    for fonction, membre in titulaires.items():
        if fonction.niveau != unite.niveau:
            raise InstallationRefusee(
                f"La fonction « {fonction.nom} » n'est pas du niveau de cette unité."
            )
        if membre.statut != Statut.ACTIF:
            raise InstallationRefusee(
                f"{membre.nom_complet} ({membre.matricule}) n'est pas un membre actif."
            )
    date_txt = date_debut.strftime("%d/%m/%Y")
    with transaction.atomic():
        anciens = list(
            _mandats_de_l_unite(unite)
            .en_cours(date_debut)
            .select_related("fonction", "membre__compte")
        )
        for m in anciens:
            m.date_fin = date_debut
            m.save(update_fields=["date_fin"])
        nouveaux = []
        for fonction, membre in titulaires.items():
            mandat = Mandat(
                membre=membre, fonction=fonction, date_debut=date_debut, installe_par=par
            )
            if unite.objet is not None:
                setattr(mandat, unite.niveau, unite.objet)
            mandat.full_clean()
            mandat.save()
            nouveaux.append(mandat)

        def prevenir():
            for m in anciens:
                notifier(
                    [m.membre.compte],
                    f"Votre mandat de {m.fonction.nom} ({unite.libelle}) a pris fin le {date_txt}.",
                )
            for m in nouveaux:
                notifier(
                    [m.membre.compte],
                    f"Vous êtes installé(e) {m.fonction.nom} ({unite.libelle}) "
                    f"à compter du {date_txt}.",
                    "/bureau/",
                )

        transaction.on_commit(prevenir)
    return nouveaux


def reinitialiser_mot_de_passe(*, cible: Membre, par) -> bytes:
    """Nouveau mot de passe provisoire ; renvoie la fiche PDF avec les identifiants.

    BNC : tout membre, sauf un compte ayant des droits que l'acteur n'a pas.
    Bureau de paroisse : ses membres, s'ils ne détiennent aucun mandat de gestion.
    """
    from django.core.exceptions import PermissionDenied
    from django.http import Http404

    from apps.bureaux.perimetre import est_bn, membres_visibles, unites_gerees
    from apps.membres.pdf import fiche_identification_pdf
    from apps.membres.services import generer_mot_de_passe_provisoire
    from apps.notifications.services import notifier

    compte = cible.compte
    if compte is None:
        raise Http404("Ce membre n'a pas de compte.")
    if par.has_perm("membres.gerer_membres"):  # BNC (mandat ou autorisation de transition)
        if not par.is_superuser and (
            compte.is_superuser or not compte.get_all_permissions() <= par.get_all_permissions()
        ):
            raise PermissionDenied("Ce compte a plus de droits que le vôtre.")
    else:
        paroisses = [u for u in unites_gerees(par) if u.niveau == "paroisse"]
        dans_ma_paroisse = any(membres_visibles(u).filter(pk=cible.pk).exists() for u in paroisses)
        if not dans_ma_paroisse or unites_gerees(compte) or est_bn(compte):
            raise PermissionDenied("Vous ne pouvez pas réinitialiser ce compte.")
    mot_de_passe = generer_mot_de_passe_provisoire()
    contenu = fiche_identification_pdf(cible, mot_de_passe)  # avant de toucher au compte
    with transaction.atomic():
        compte.set_password(mot_de_passe)
        compte.doit_changer_mot_de_passe = True
        compte.save(update_fields=["password", "doit_changer_mot_de_passe"])
        auteur = str(par)
        transaction.on_commit(
            lambda: notifier([compte], f"Votre mot de passe a été réinitialisé par {auteur}.")
        )
    return contenu
