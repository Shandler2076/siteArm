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


DIRECTION = ("Président", "Secrétaire national")
MOTIFS_DEPART = {
    "demission": "Démission",
    "voyage": "Voyage ou absence prolongée",
    "deces": "Décès",
    "mutation": "Mutation",
    "sanction": "Sanction",
    "incoherent": "Nomination hors de sa zone (correction)",
    "autre": "Autre motif",
}


_A_CHERCHER = object()


def raison_hors_zone(unite: Unite, membre: Membre, actuelle=_A_CHERCHER) -> str:
    """Vide si le membre est de la zone de l'unité ; sinon la raison du refus.

    Décision du 19/11/2026 : on n'est membre du bureau d'une paroisse, d'un circuit ou d'une
    région que si sa paroisse actuelle s'y trouve. Le Bureau National de Commandement est
    ouvert à tout membre actif du pays."""
    if unite.niveau == "national":
        return ""
    if actuelle is _A_CHERCHER:
        actuelle = membre.affectation_actuelle
    if actuelle is None:
        return f"{membre.nom_complet} ({membre.matricule}) n'a pas de paroisse actuelle."
    paroisse = actuelle.paroisse
    if unite.niveau == "paroisse" and paroisse != unite.objet:
        return (
            f"{membre.nom_complet} ({membre.matricule}) est de la paroisse {paroisse.nom}, "
            f"pas de {unite.objet.nom}."
        )
    if unite.niveau == "circuit" and paroisse.circuit_id != unite.objet.pk:
        return (
            f"{membre.nom_complet} ({membre.matricule}) est du circuit {paroisse.circuit.nom}, "
            f"pas du circuit {unite.objet.nom}."
        )
    if unite.niveau == "region" and paroisse.circuit.region_id != unite.objet.pk:
        return (
            f"{membre.nom_complet} ({membre.matricule}) est de la région "
            f"{paroisse.circuit.region.nom}, pas de la région {unite.objet.nom}."
        )
    return ""


def _verifier_titulaire(unite: Unite, fonction: Fonction, membre: Membre) -> None:
    if fonction.niveau != unite.niveau:
        raise InstallationRefusee(
            f"La fonction « {fonction.nom} » n'est pas du niveau de cette unité."
        )
    if membre.statut != Statut.ACTIF:
        raise InstallationRefusee(
            f"{membre.nom_complet} ({membre.matricule}) n'est pas un membre actif."
        )
    raison = raison_hors_zone(unite, membre)
    if raison:
        raise InstallationRefusee(raison)


def installer_bureau(
    *, unite: Unite, titulaires: dict[Fonction, Membre], date_debut: datetime.date, par
) -> list[Mandat]:
    """Clôt tous les mandats en cours de l'unité et installe les nouveaux titulaires."""
    from apps.notifications.services import notifier

    if not titulaires:
        raise InstallationRefusee("Indiquez au moins un titulaire.")
    for fonction, membre in titulaires.items():
        _verifier_titulaire(unite, fonction, membre)
    if unite.niveau == "national" and not any(
        f.nom in ("Président", "Secrétaire national") for f in titulaires
    ):
        raise InstallationRefusee(
            "Le Bureau National de Commandement doit avoir au moins un Président ou Secrétaire "
            "national : sinon plus personne ne pourrait installer les bureaux."
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
                    "/membres/ma-fiche/",
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


def _fin_du_bureau(unite: Unite, jour: datetime.date):
    """(fin prévue, fin déjà fixée ou None) du mandat en cours du bureau : la plus fréquente
    parmi ses mandats. (None, None) si aucun bureau n'est en place."""
    from collections import Counter

    fins = Counter(
        _mandats_de_l_unite(unite).en_cours(jour).values_list("date_fin_prevue", "date_fin")
    )
    return fins.most_common(1)[0][0] if fins else (None, None)


def _nouveau_mandat(unite, fonction, membre, date_debut, fin_prevue, par, fin=None) -> Mandat:
    """`fin` : un nouveau bureau est déjà fixé (installé à l'avance) → le mandat s'y arrête."""
    mandat = Mandat(
        membre=membre,
        fonction=fonction,
        date_debut=date_debut,
        date_fin_prevue=fin_prevue,
        date_fin=fin,
        installe_par=par,
    )
    if unite.objet is not None:
        setattr(mandat, unite.niveau, unite.objet)
    mandat.full_clean()
    mandat.save()
    return mandat


def remplacer_titulaire(
    *, mandat: Mandat, date: datetime.date, motif: str, remplacant: Membre | None, par
) -> Mandat | None:
    """Ferme le mandat d'UN titulaire (les autres ne bougent pas) ; le remplaçant éventuel
    termine le mandat en cours, à la même date de fin prévue. Sans remplaçant : poste vacant."""
    from apps.bureaux.perimetre import Unite as _Unite
    from apps.journal.models import TITULAIRE_REMPLACE
    from apps.journal.services import journaliser
    from apps.notifications.services import notifier

    if motif not in MOTIFS_DEPART:
        raise InstallationRefusee("Choisissez le motif du départ.")
    unite = _Unite(mandat.fonction.niveau, mandat.unite)
    with transaction.atomic():
        from django.utils import timezone

        aujourd_hui = timezone.localdate()
        mandat = Mandat.objects.select_for_update().get(pk=mandat.pk)
        fin_fixee = mandat.date_fin
        if fin_fixee is not None and (fin_fixee <= date or fin_fixee <= aujourd_hui):
            raise InstallationRefusee("Ce mandat est déjà terminé.")
        if date <= mandat.date_debut:
            # Seule exception : annuler une nomination hors zone qui n'a pas encore commencé
            # (ou commence aujourd'hui) — jamais effacer un mandat déjà exercé.
            if motif != "incoherent" or remplacant is not None or mandat.date_debut < aujourd_hui:
                raise InstallationRefusee(
                    "La date de départ doit suivre la date de début du mandat."
                )
            date = mandat.date_debut
        if remplacant is not None:
            _verifier_titulaire(unite, mandat.fonction, remplacant)
        elif unite.niveau == "national" and mandat.fonction.nom in DIRECTION:
            restants = (
                Mandat.objects.en_cours(date)
                .filter(fonction__niveau="national", fonction__nom__in=DIRECTION)
                .exclude(pk=mandat.pk)
                .filter(membre__statut=Statut.ACTIF)
            )
            if not restants.exists():
                raise InstallationRefusee(
                    "Le Bureau National de Commandement doit garder un Président ou Secrétaire "
                    "national : nommez un remplaçant."
                )
        mandat.date_fin = date
        mandat.save(update_fields=["date_fin"])
        nouveau = None
        if remplacant is not None:
            # Il termine le mandat en cours : même fin prévue, et même fin déjà fixée s'il y en a.
            nouveau = _nouveau_mandat(
                unite, mandat.fonction, remplacant, date, mandat.date_fin_prevue, par, fin_fixee
            )
        date_txt = date.strftime("%d/%m/%Y")
        partant, fonction = mandat.membre, mandat.fonction

        def prevenir():
            notifier(
                [partant.compte],
                f"Votre mandat de {fonction.nom} ({unite.libelle}) a pris fin le {date_txt}.",
                "/membres/ma-fiche/",
            )
            if nouveau is not None:
                notifier(
                    [nouveau.membre.compte],
                    f"Vous êtes installé(e) {fonction.nom} ({unite.libelle}) à compter du "
                    f"{date_txt}, jusqu'à la fin du mandat en cours.",
                    "/bureau/",
                )

        transaction.on_commit(prevenir)
    journaliser(
        par,
        TITULAIRE_REMPLACE,
        unite=unite.cle,
        fonction=fonction.nom,
        membre=partant.matricule,
        remplacant=remplacant.matricule if remplacant else "",
        motif=motif,
        date=date.isoformat(),
    )
    return nouveau


def pourvoir_poste(
    *, unite: Unite, fonction: Fonction, membre: Membre, date_debut: datetime.date, par
) -> Mandat:
    """Nomme UNE personne à un poste vacant ; elle termine le mandat en cours du bureau."""
    from apps.journal.models import POSTE_POURVU
    from apps.journal.services import journaliser
    from apps.notifications.services import notifier

    _verifier_titulaire(unite, fonction, membre)
    with transaction.atomic():
        occupe = (
            _mandats_de_l_unite(unite)
            .select_for_update()
            .filter(fonction=fonction)
            .filter(Q(date_fin__isnull=True) | Q(date_fin__gt=date_debut))
            .exists()  # en cours, ou déjà prévu plus tard
        )
        if occupe:
            raise InstallationRefusee(
                f"Le poste de {fonction.nom} est déjà occupé : utilisez « Remplacer »."
            )
        fin_prevue, fin_fixee = _fin_du_bureau(unite, date_debut)
        if fin_prevue is None:
            raise InstallationRefusee(
                "Aucun bureau n'est en place dans cette unité : installez d'abord un bureau."
            )
        mandat = _nouveau_mandat(unite, fonction, membre, date_debut, fin_prevue, par, fin_fixee)
        date_txt = date_debut.strftime("%d/%m/%Y")
        transaction.on_commit(
            lambda: notifier(
                [membre.compte],
                f"Vous êtes installé(e) {fonction.nom} ({unite.libelle}) à compter du "
                f"{date_txt}, jusqu'à la fin du mandat en cours.",
                "/bureau/",
            )
        )
    journaliser(
        par,
        POSTE_POURVU,
        unite=unite.cle,
        fonction=fonction.nom,
        membre=membre.matricule,
        date=date_debut.isoformat(),
    )
    return mandat


def modifier_droit(*, fonction: Fonction, case: str, valeur: bool, par) -> Fonction:
    """Coche ou décoche une case de « Fonctions et droits » (cases nationales : fonctions
    nationales seulement)."""
    from apps.bureaux.perimetre import DROITS_PAR_CASE
    from apps.journal.models import DROITS_MODIFIES
    from apps.journal.services import journaliser

    permises = DROITS_PAR_CASE if fonction.niveau == "national" else {"droit_gerer": None}
    if case not in permises:
        raise InstallationRefusee("Ce droit ne s'applique pas à cette fonction.")
    setattr(fonction, case, bool(valeur))
    fonction.save(update_fields=[case])
    libelle = Fonction._meta.get_field(case).verbose_name
    journaliser(par, DROITS_MODIFIES, fonction=fonction.nom, case=str(libelle), valeur=bool(valeur))
    return fonction


def mandats_incoherents(jour: datetime.date | None = None) -> list[tuple[Mandat, str]]:
    """Mandats en cours (ou à venir) dont le titulaire n'est pas de la zone, ou n'est plus actif
    (enregistrés avant le contrôle du 19/11/2026) : à fermer par le BNC."""
    from django.utils import timezone

    from apps.bureaux.perimetre import Unite as _Unite

    j = jour or timezone.localdate()
    resultat = []
    from django.db.models import Prefetch

    from apps.membres.models import Affectation

    mandats = (
        Mandat.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gt=j))
        .select_related("fonction", "membre", "paroisse", "circuit", "region")
        .prefetch_related(
            Prefetch(
                "membre__affectations",
                queryset=Affectation.objects.filter(date_fin__isnull=True).select_related(
                    "paroisse__circuit__region"
                ),
                to_attr="affectations_ouvertes",
            )
        )
        .order_by("fonction__niveau", "date_debut")
    )
    for m in mandats:
        if m.membre.statut != Statut.ACTIF:
            resultat.append((m, f"{m.membre.nom_complet} n'est plus un membre actif."))
            continue
        ouvertes = m.membre.affectations_ouvertes
        raison = raison_hors_zone(
            _Unite(m.fonction.niveau, m.unite), m.membre, ouvertes[0] if ouvertes else None
        )
        if raison:
            resultat.append((m, raison))
    return resultat


def _mandat_en_cours_ou_a_venir(membre) -> bool:
    """Un mandat pas encore terminé (même s'il ne commence que plus tard) protège le compte."""
    from django.utils import timezone

    return (
        Mandat.objects.filter(membre=membre)
        .filter(Q(date_fin__isnull=True) | Q(date_fin__gt=timezone.localdate()))
        .exists()
    )


def reinitialiser_mot_de_passe(*, cible: Membre, par) -> bytes:
    """Nouveau mot de passe provisoire ; renvoie la fiche PDF avec les identifiants.

    BNC : tout membre, sauf un compte ayant des droits que l'acteur n'a pas.
    Bureau de paroisse : ses membres simples seulement. Un membre qui a une fonction en
    cours (trésorier, secrétaire, chef…) n'est réinitialisé que par le BNC.
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
            or _mandat_en_cours_ou_a_venir(cible)
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


DELAI_ALERTE = datetime.timedelta(days=30)
PALIERS = (30, 14, 7)  # jours avant la fin du mandat d'un bureau (décision du 19/11/2026)


def nom_du_bureau(unite) -> str:
    """« du bureau de la Paroisse P1 », « du bureau du Circuit X », « du BNC… »."""
    from apps.bureaux.perimetre import Niveau

    if unite.niveau == Niveau.NATIONAL:
        return "du Bureau National de Commandement"
    article = "du" if unite.niveau == Niveau.CIRCUIT else "de la"
    return f"du bureau {article} {unite.libelle}"


def bureaux_a_echeance(jour: datetime.date, horizon: datetime.timedelta = DELAI_ALERTE):
    """[(unité, date de fin, mandats)] des bureaux dont le mandat finit avant `jour + horizon`
    (ou est déjà échu), un élément par bureau et par date de fin."""
    from apps.bureaux.perimetre import Unite

    groupes: dict = {}
    mandats = (
        Mandat.objects.en_cours(jour)
        .filter(date_fin_prevue__lte=jour + horizon)
        .select_related("fonction", "membre__compte", "paroisse", "circuit", "region")
        .order_by("date_fin_prevue")
    )
    for m in mandats:
        unite = Unite(m.fonction.niveau, m.unite)
        groupes.setdefault((unite.cle, m.date_fin_prevue), (unite, m.date_fin_prevue, []))[
            2
        ].append(m)
    return sorted(groupes.values(), key=lambda g: (g[1], g[0].cle))


def alertes_echeances(jour: datetime.date | None = None) -> tuple[int, int]:
    """Prévient chaque bureau (ses membres et le BNC) à 30, 14 et 7 jours de la fin
    de son mandat, puis à l'échéance. Une seule alerte par bureau et par palier. Ne coupe rien."""
    from django.utils import timezone

    from apps.bureaux.models import AlerteBureau
    from apps.bureaux.perimetre import Unite, titulaires_gestion
    from apps.notifications.services import notifier

    j = jour or timezone.localdate()
    echeances = echus = 0
    nationaux = list(titulaires_gestion(Unite("national", None)))
    for unite, fin, mandats in bureaux_a_echeance(j):
        jours = (fin - j).days
        palier = 0 if jours <= 0 else min(p for p in PALIERS if jours <= p)
        _alerte, creee = AlerteBureau.objects.get_or_create(
            unite_cle=unite.cle, date_fin=fin, palier=palier, defaults={"envoyee_le": j}
        )
        if not creee:
            continue
        date = fin.strftime("%d/%m/%Y")
        if palier:
            texte = (
                f"Le mandat {nom_du_bureau(unite)} arrive à échéance le {date} "
                f"(dans {jours} jour{'s' if jours > 1 else ''})."
            )
            echeances += 1
        else:
            texte = (
                f"Le mandat {nom_du_bureau(unite)} est arrivé à échéance le {date} : "
                "installez le nouveau bureau."
            )
            echus += 1
        destinataires = [m.membre.compte for m in mandats if m.membre.compte_id] + nationaux
        notifier(destinataires, texte, "/")
    return echeances, echus


def libelles_fonctions(compte, jour: datetime.date | None = None) -> list[str]:
    """Fonctions en cours d'une personne, de la paroisse au national, une par ligne :
    « Secrétaire paroissial — Paroisse X », « Trésorier régional — Région Y »…"""
    from apps.bureaux.perimetre import ORDRE, Unite

    if not getattr(compte, "is_authenticated", False):
        return []
    mandats = (
        Mandat.objects.en_cours(jour)
        .filter(membre__compte=compte)
        .select_related("fonction", "paroisse", "circuit", "region")
    )
    tries = sorted(mandats, key=lambda m: (-ORDRE[m.fonction.niveau], m.fonction.ordre))
    return [f"{m.fonction.nom} — {Unite(m.fonction.niveau, m.unite).libelle}" for m in tries]
