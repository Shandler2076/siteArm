import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.bureaux.models import Fonction, Niveau
from apps.bureaux.perimetre import MODELES, Unite, est_bn
from apps.bureaux.services import InstallationRefusee, _mandats_de_l_unite, installer_bureau
from apps.comptes.models import normaliser_identifiant
from apps.membres.models import Membre


def bn_requis(vue):
    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not est_bn(request.user):
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
    from django.utils import timezone

    from apps.bureaux.models import Mandat
    from apps.bureaux.services import DELAI_ALERTE

    j = timezone.localdate()
    mandats = (
        Mandat.objects.en_cours(j)
        .filter(date_fin_prevue__lte=j + DELAI_ALERTE)
        .select_related("fonction", "membre", "paroisse", "circuit", "region")
        .order_by("date_fin_prevue")
    )
    lignes = [
        {"mandat": m, "unite": Unite(m.fonction.niveau, m.unite), "echu": m.date_fin_prevue <= j}
        for m in mandats
    ]
    return render(request, "bureaux/bn_echeances.html", {"lignes": lignes})
