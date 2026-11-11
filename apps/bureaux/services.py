"""Services des bureaux : installation des bureaux, réinitialisation, échéances."""

import datetime

from django.db import transaction
from django.db.models import Q

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
    if unite.niveau == "national" and not any(f.droit_gerer for f in titulaires):
        raise InstallationRefusee(
            "Le Bureau National doit avoir au moins un Président ou Secrétaire national "
            "(une fonction qui gère le site) : sinon plus personne ne pourrait gérer le site."
        )
    plus_recent = (
        _mandats_de_l_unite(unite)
        .filter(date_debut__gte=date_debut)
        .order_by("-date_debut")
        .first()
    )
    if plus_recent is not None:
        raise InstallationRefusee(
            "Un bureau plus récent existe déjà (installé le "
            f"{plus_recent.date_debut:%d/%m/%Y}) : choisissez une date de début postérieure."
        )
    date_txt = date_debut.strftime("%d/%m/%Y")
    with transaction.atomic():
        # Tous les mandats encore ouverts de l'unité (aucun ne commence après date_debut).
        anciens = list(
            _mandats_de_l_unite(unite)
            .filter(Q(date_fin__isnull=True) | Q(date_fin__gt=date_debut))
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
    from apps.journal.models import INSTALLATION_BUREAU
    from apps.journal.services import journaliser

    journaliser(
        par,
        INSTALLATION_BUREAU,
        unite=unite.cle,
        titulaires={f.nom: m.matricule for f, m in titulaires.items()},
        date_debut=date_debut.isoformat(),
    )
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
        droits_particuliers = (
            compte.is_staff
            or compte.is_superuser
            or bool(compte.get_all_permissions())
            or bool(unites_gerees(compte))
            or est_bn(compte)
        )
        if not dans_ma_paroisse or droits_particuliers:
            raise PermissionDenied("Vous ne pouvez pas réinitialiser ce compte.")
    from apps.journal.models import REINITIALISATION
    from apps.journal.services import journaliser

    mot_de_passe = generer_mot_de_passe_provisoire()
    contenu = fiche_identification_pdf(cible, mot_de_passe)  # avant de toucher au compte
    journaliser(par, REINITIALISATION, membre=cible.matricule)
    with transaction.atomic():
        compte.set_password(mot_de_passe)
        compte.doit_changer_mot_de_passe = True
        compte.save(update_fields=["password", "doit_changer_mot_de_passe"])
        auteur = str(par)
        transaction.on_commit(
            lambda: notifier([compte], f"Votre mot de passe a été réinitialisé par {auteur}.")
        )
    return contenu


DELAI_ALERTE = datetime.timedelta(days=60)


def _destinataires_echeance(mandat: Mandat):
    from apps.bureaux.perimetre import Unite, titulaires_gestion

    unite = Unite(mandat.fonction.niveau, mandat.unite)
    return [
        mandat.membre.compte,
        *titulaires_gestion(unite),
        *titulaires_gestion(Unite("national", None)),
    ]


def alertes_echeances(jour: datetime.date | None = None) -> tuple[int, int]:
    """Prévient 60 jours avant la fin prévue, puis quand le mandat est échu. Ne coupe rien."""
    from django.utils import timezone

    from apps.bureaux.perimetre import Unite
    from apps.notifications.services import notifier

    j = jour or timezone.localdate()
    echeances = echus = 0
    mandats = (
        Mandat.objects.en_cours(j)
        .filter(date_fin_prevue__lte=j + DELAI_ALERTE)
        .select_related("fonction", "membre__compte", "paroisse", "circuit", "region")
    )
    for m in mandats:
        unite = Unite(m.fonction.niveau, m.unite)
        texte = f"Le mandat de {m.fonction.nom} ({unite.libelle}) de {m.membre.nom_complet}"
        fin = m.date_fin_prevue.strftime("%d/%m/%Y")
        if m.date_fin_prevue > j and m.alerte_echeance_le is None:
            notifier(_destinataires_echeance(m), f"{texte} arrive à échéance le {fin}.", "/")
            m.alerte_echeance_le = j
            m.save(update_fields=["alerte_echeance_le"])
            echeances += 1
        elif m.date_fin_prevue <= j and m.alerte_echu_le is None:
            notifier(
                _destinataires_echeance(m),
                f"{texte} est échu depuis le {fin} et n'a pas été renouvelé.",
                "/",  # l'accueil montre à chacun les liens auxquels il a droit
            )
            m.alerte_echu_le = j
            m.save(update_fields=["alerte_echu_le"])
            echus += 1
    return echeances, echus
