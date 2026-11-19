import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.bureaux.models import Fonction, Niveau
from apps.bureaux.perimetre import MODELES, Unite
from apps.bureaux.services import InstallationRefusee, _mandats_de_l_unite, installer_bureau
from apps.comptes.models import normaliser_identifiant
from apps.membres.models import Membre


def bn_requis(vue):
    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        # Mandat national de gestion (via MandatBackend) ou autorisation de transition.
        if not request.user.has_perm("membres.gerer_membres"):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


def _unite(niveau, ident):
    if niveau == Niveau.NATIONAL:
        return Unite(Niveau.NATIONAL, None)
    if niveau in MODELES and str(ident or "").isdigit():
        objet = MODELES[niveau].objects.filter(pk=int(ident), active=True).first()
        if objet:
            return Unite(niveau, objet)
    return None


@bn_requis
def installer(request):
    source = request.POST if request.method == "POST" else request.GET
    niveau = source.get("niveau", "")
    unite = _unite(niveau, source.get("unite"))
    contexte = {"niveaux": Niveau.choices, "niveau": niveau, "unite": unite, "erreurs": []}
    if niveau in MODELES and unite is None:
        contexte["choix_unites"] = MODELES[niveau].objects.filter(active=True).order_by("nom")
    if unite is None:
        return render(request, "bureaux/bn_installer.html", contexte)

    fonctions = list(Fonction.objects.filter(niveau=unite.niveau).order_by("ordre"))
    actuels = {
        m.fonction_id: m for m in _mandats_de_l_unite(unite).en_cours().select_related("membre")
    }
    saisies = {f.pk: (source.get(f"fonction_{f.pk}") or "").strip() for f in fonctions}
    contexte.update(
        fonctions=[(f, actuels.get(f.pk), saisies[f.pk]) for f in fonctions],
        date_debut=source.get("date_debut", ""),
    )
    if request.method == "POST":
        try:
            date_debut = datetime.date.fromisoformat(source.get("date_debut", ""))
        except ValueError:
            contexte["erreurs"].append("Indiquez une date de début valide.")
            date_debut = None
        titulaires = {}
        for f in fonctions:
            if not saisies[f.pk]:
                continue
            matricule = normaliser_identifiant(saisies[f.pk])
            membre = Membre.objects.filter(matricule=matricule).first()
            if membre is None:
                contexte["erreurs"].append(f"Matricule inconnu : {matricule}")
            else:
                titulaires[f] = membre
        if not contexte["erreurs"]:
            try:
                nouveaux = installer_bureau(
                    unite=unite, titulaires=titulaires, date_debut=date_debut, par=request.user
                )
            except InstallationRefusee as e:
                contexte["erreurs"].append(str(e))
            else:
                messages.success(request, f"Bureau installé : {len(nouveaux)} mandat(s).")
                params = f"?niveau={unite.niveau}" + (
                    f"&unite={unite.objet.pk}" if unite.objet else ""
                )
                return redirect(reverse("bureaux:bn_installer") + params)
    return render(request, "bureaux/bn_installer.html", contexte)


@bn_requis
def fonctions(request):
    if request.method == "POST":
        f = get_object_or_404(Fonction, pk=request.POST.get("fonction"))
        f.droit_gerer = request.POST.get("droit_gerer") == "on"
        f.save(update_fields=["droit_gerer"])
        etat = "peut" if f.droit_gerer else "ne peut plus"
        messages.success(request, f"La fonction « {f.nom} » {etat} gérer le site.")
        return redirect("bureaux:bn_fonctions")
    par_niveau = [
        (libelle, Fonction.objects.filter(niveau=valeur).order_by("ordre"))
        for valeur, libelle in Niveau.choices
    ]
    return render(request, "bureaux/bn_fonctions.html", {"par_niveau": par_niveau})


@bn_requis
def echeances(request):
    """Échéances par bureau (décision du 19/11/2026) : un bureau, pas une personne."""
    from django.utils import timezone

    from apps.bureaux.services import bureaux_a_echeance

    j = timezone.localdate()
    lignes = [
        {"unite": unite, "fin": fin, "jours": (fin - j).days, "echu": fin <= j, "nombre": len(m)}
        for unite, fin, m in bureaux_a_echeance(j)
    ]
    return render(request, "bureaux/bn_echeances.html", {"lignes": lignes})


def _bureaux_installes(jour=None) -> dict:
    """{clé d'unité : mandats en cours} pour tous les bureaux installés, en une requête."""
    from apps.bureaux.models import Mandat

    installes: dict = {}
    for m in (
        Mandat.objects.en_cours(jour)
        .select_related("fonction", "membre")
        .order_by("fonction__ordre")
    ):
        niveau = m.fonction.niveau
        cle = "national" if niveau == Niveau.NATIONAL else f"{niveau}-{getattr(m, niveau + '_id')}"
        installes.setdefault(cle, []).append(m)
    return installes


@bn_requis
def bureaux_en_place(request):
    """Tableaux par région : circuits et paroisses, installés ou non (décision du 19/11/2026)."""
    from apps.organisation.models import Circuit, Paroisse, Region

    installes = _bureaux_installes()
    paroisses: dict = {}
    for p in Paroisse.objects.filter(active=True).order_by("nom"):
        paroisses.setdefault(p.circuit_id, []).append(
            {"objet": p, "cle": f"paroisse-{p.pk}", "installe": f"paroisse-{p.pk}" in installes}
        )
    circuits: dict = {}
    for c in Circuit.objects.filter(active=True).order_by("nom"):
        circuits.setdefault(c.region_id, []).append(
            {
                "objet": c,
                "cle": f"circuit-{c.pk}",
                "installe": f"circuit-{c.pk}" in installes,
                "paroisses": paroisses.get(c.pk, []),
            }
        )
    regions = []
    for r in Region.objects.filter(active=True).order_by("code"):
        lignes = circuits.get(r.pk, [])
        toutes = [p for c in lignes for p in c["paroisses"]]
        regions.append(
            {
                "objet": r,
                "cle": f"region-{r.pk}",
                "installe": f"region-{r.pk}" in installes,
                "circuits": lignes,
                "nb_paroisses": len(toutes),
                "nb_installees": sum(1 for p in toutes if p["installe"]),
            }
        )
    return render(
        request,
        "bureaux/bn_bureaux.html",
        {"regions": regions, "national_installe": "national" in installes},
    )


@bn_requis
def bureau_en_place(request, cle):
    """Composition d'un bureau installé : matricule, noms, postes."""
    from django.http import Http404

    from apps.bureaux.perimetre import unite_par_cle

    unite = unite_par_cle(cle)
    if unite is None:
        raise Http404
    mandats = _bureaux_installes().get(unite.cle, [])
    return render(request, "bureaux/bn_bureau.html", {"unite": unite, "mandats": mandats})
