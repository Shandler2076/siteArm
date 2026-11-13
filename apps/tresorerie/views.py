"""Pages de la trésorerie (décisions du mainteneur du 13/11/2026).

Droits : le gardien des périmètres (`unites_tresorerie`, `est_tresorier_national`,
`est_validateur_reversements`) et `membres.gerer_membres` pour le BN.
"""

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bureaux.perimetre import (
    Niveau,
    Unite,
    est_tresorier_national,
    est_validateur_reversements,
    peut_agir_tresorerie,
    peut_voir_cotisations_de,
    peut_voir_tresorerie,
)
from apps.membres.models import Membre, Statut
from apps.tresorerie import services as s
from apps.tresorerie.models import (
    Contribution,
    CotisationSpeciale,
    EtatPaiement,
    EtatReversement,
    NumeroMobileMoney,
    Paiement,
    PourMembres,
    Reversement,
    TypeMontant,
)


def _bn(user) -> bool:
    return user.has_perm("membres.gerer_membres")


def _membre(user):
    try:
        return user.membre
    except Membre.DoesNotExist:
        return None


def _vers_plateforme(paiement: Paiement):
    """Plateforme simulée (site d'essai) : page de confirmation ; une vraie plateforme redirigera
    vers son propre écran et confirmera par son retour signé."""
    return redirect("tresorerie:paiement", reference=paiement.reference)


def confirmation_reduite(membre) -> str:
    """« Soldat Albert A. — Paroisse de GBOA » : rien de plus (décision du 13/11/2026)."""
    grade = membre.get_grade_display() if membre.grade else "Camarade"
    initiale = (membre.nom or "?")[:1].upper()
    a = membre.affectation_actuelle
    paroisse = f" — {a.paroisse.nom}" if a else ""
    prenom = (membre.prenoms or "").split(" ")[0]
    return f"{grade} {prenom} {initiale}.{paroisse}"


# --- Membre : payer ------------------------------------------------------------------------------


@login_required
def payer(request):
    """Payer ses propres mois de cotisation par mobile money."""
    membre = _membre(request.user)
    if membre is None:
        raise Http404
    if request.method == "POST":
        try:
            p = s.initier_paiement_mensuel(
                request.user, [(membre, _entier(request.POST.get("nombre")))]
            )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
            return redirect("tresorerie:payer")
        return _vers_plateforme(p)
    return render(
        request,
        "tresorerie/payer.html",
        {"membre": membre, "speciales": s.speciales_du_membre(membre)},
    )


def _entier(valeur) -> int:
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return 0


@login_required
def payer_pour(request):
    """Payer pour un autre membre (n'importe quel membre peut aider) : matricule, confirmation
    réduite, nombre de mois ou cotisation spéciale."""
    if _membre(request.user) is None and not _bn(request.user):
        raise Http404
    matricule = (request.POST.get("matricule") or request.GET.get("matricule") or "").strip()
    beneficiaire = (
        Membre.objects.filter(
            matricule=matricule.upper(), statut__in=[Statut.ACTIF, Statut.SANCTIONNE]
        ).first()
        if matricule
        else None
    )
    soi_meme = beneficiaire is not None and beneficiaire.compte_id == request.user.pk
    if request.method == "POST" and beneficiaire and request.POST.get("confirmer"):
        try:
            cs_pk = request.POST.get("speciale", "")
            if cs_pk.isdigit():
                cs = get_object_or_404(CotisationSpeciale, pk=int(cs_pk))
                p = s.initier_paiement_special(
                    request.user, cs, _entier(request.POST.get("montant")), membre=beneficiaire
                )
            else:
                p = s.initier_paiement_mensuel(
                    request.user, [(beneficiaire, _entier(request.POST.get("nombre")))]
                )
        except s.TresorerieRefusee as e:
            # Pour un tiers, message général : ne rien révéler de la situation du membre aidé.
            messages.error(
                request,
                str(e)
                if soi_meme
                else "Ce paiement n'est pas possible pour ce membre (nombre de mois ou montant "
                "trop élevé, ou cotisations non ouvertes). Essayez un montant plus petit.",
            )
        else:
            return _vers_plateforme(p)
    # Seules les cotisations spéciales demandées à TOUS les membres sont proposées : une
    # cotisation ciblée révélerait le grade, l'âge ou la catégorie du membre aidé.
    speciales = [
        x["cs"]
        for x in (s.speciales_du_membre(beneficiaire) if beneficiaire else [])
        if x["cs"].pour_membres == PourMembres.TOUS or (x["cs"].sanction_id and not x["reglee"])
    ]
    return render(
        request,
        "tresorerie/payer_pour.html",
        {
            "matricule": matricule,
            "beneficiaire": beneficiaire,
            "confirmation": confirmation_reduite(beneficiaire) if beneficiaire else "",
            "introuvable": bool(matricule) and beneficiaire is None,
            "speciales": speciales,
        },
    )


@login_required
def payer_speciale(request, pk):
    """Payer une cotisation spéciale pour soi, ou au nom d'un bureau (Trésorier)."""
    cs = get_object_or_404(CotisationSpeciale, pk=pk, ouverte=True)
    cle = request.GET.get("bureau") or request.POST.get("bureau") or ""
    type_payeur = request.GET.get("type") or request.POST.get("type") or "bureau"
    if type_payeur not in s.TYPES_PAYEUR:
        raise Http404
    unite = s.unite_par_cle(cle) if cle else None
    if unite is not None and not peut_agir_tresorerie(request.user, unite):
        raise PermissionDenied
    membre = None if unite else _membre(request.user)
    if unite is None and membre is None:
        raise Http404
    cle_p = s.cle_payeur(type_payeur, unite) if unite else ""
    reste = s.reste_a_payer(cs, membre=membre, unite_cle=cle_p)
    if request.method == "POST":
        try:
            p = s.initier_paiement_special(
                request.user,
                cs,
                _entier(request.POST.get("montant")),
                membre=membre,
                unite=unite,
                type_payeur=type_payeur,
            )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            return _vers_plateforme(p)
    return render(
        request,
        "tresorerie/payer_speciale.html",
        {
            "cs": cs,
            "unite": unite,
            "type_payeur": type_payeur,
            "pour": s.libelle_payeur(type_payeur, unite) if unite else "",
            "reste": reste,
            "TypeMontant": TypeMontant,
        },
    )


@login_required
def paiement(request, reference):
    """Plateforme simulée : seul le payeur voit et confirme son paiement."""
    p = get_object_or_404(Paiement, reference=reference, payeur=request.user)
    if s.p_simule_interdit(p):
        raise Http404
    if request.method == "POST" and p.etat == EtatPaiement.EN_ATTENTE:
        if request.POST.get("action") == "confirmer":
            p = s.confirmer_paiement(p)
            if p.etat == EtatPaiement.CONFIRME:
                messages.success(request, f"Paiement confirmé : {p.montant} F.")
            else:
                messages.error(request, p.message)
        else:
            s.echouer_paiement(p, "Paiement annulé par le payeur.")
            messages.info(request, "Paiement annulé : rien n'a été prélevé.")
        return redirect("tresorerie:paiement", reference=p.reference)
    return render(request, "tresorerie/paiement.html", {"p": p})


@login_required
def quittance(request, pk):
    c = get_object_or_404(
        Contribution.objects.select_related("cotisation", "membre", "paiement"), pk=pk
    )
    autorise = (
        _bn(request.user)
        or est_tresorier_national(request.user)
        or c.paiement.payeur_id == request.user.pk
        or (c.membre is not None and c.membre.compte_id == request.user.pk)
        or (c.membre is not None and peut_voir_cotisations_de(request.user, c.membre))
        or (c.unite_cle and _peut_voir_cle(request.user, c.unite_cle))
    )
    if not autorise:
        raise Http404
    from apps.tresorerie.pdf import quittance_pdf

    r = HttpResponse(quittance_pdf(c), content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="quittance-{c.quittance}.pdf"'
    r["Cache-Control"] = "private, no-store"
    return r


def _peut_voir_cle(user, cle) -> bool:
    unite = s.unite_par_cle((cle or "").removeprefix("unite:"))
    return unite is not None and peut_voir_tresorerie(user, unite)


# --- Espace de trésorerie d'un bureau ---------------------------------------------------------


@login_required
def espace(request, cle):
    unite = s.unite_par_cle(cle)
    if (
        unite is None
        or unite.niveau == Niveau.NATIONAL
        or not peut_voir_tresorerie(request.user, unite)
    ):
        raise Http404
    agit = peut_agir_tresorerie(request.user, unite)
    from apps.cotisations.models import EtatVersement, ModeVersement, Versement

    filtre = {"paroisse": unite.objet}
    if unite.niveau == Niveau.CIRCUIT:
        filtre = {"paroisse__circuit": unite.objet}
    elif unite.niveau == Niveau.REGION:
        filtre = {"paroisse__circuit__region": unite.objet}
    versements = (
        Versement.objects.filter(
            mode=ModeVersement.MOBILE_MONEY, etat=EtatVersement.VALIDE, **filtre
        )
        .select_related("membre", "paroisse")
        .order_by("-date_validation")[:50]
    )
    return render(
        request,
        "tresorerie/espace.html",
        {
            "unite": unite,
            "agit": agit,
            "versements": versements,
            "reversements": Reversement.objects.filter(cle=unite.cle).order_by("-mois")[:24],
            "speciales": s.speciales_du_bureau(unite),
            "contributions": Contribution.objects.filter(
                unite_cle__in=[unite.cle, s.cle_payeur("unite", unite)]
            ).select_related("cotisation")[:50],
            "numero": NumeroMobileMoney.objects.filter(cle=unite.cle).first(),
        },
    )


@login_required
def payer_membres(request, cle):
    """Trésorier de paroisse : payer pour plusieurs membres (espèces reçues) par mobile money."""
    unite = s.unite_par_cle(cle)
    if unite is None or unite.niveau != Niveau.PAROISSE:
        raise Http404
    if not peut_agir_tresorerie(request.user, unite):
        raise PermissionDenied
    from apps.bureaux.perimetre import membres_visibles

    membres = list(membres_visibles(unite).order_by("nom", "prenoms"))
    if request.method == "POST":
        lignes = [(m, _entier(request.POST.get(f"n{m.pk}"))) for m in membres]
        try:
            p = s.initier_paiement_mensuel(request.user, [(m, n) for m, n in lignes if n > 0])
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            return _vers_plateforme(p)
    return render(request, "tresorerie/payer_membres.html", {"unite": unite, "membres": membres})


# --- Bureau national ----------------------------------------------------------------------------


CRITERES = (
    "sexe",
    "categorie",
    "grade",
    "grade_min",
    "region",
    "circuit",
    "paroisse",
    "age",
    "age_x",
    "age_y",
)


def _entier_ou_none(valeur):
    n = _entier(valeur)
    return n if n > 0 else None


@login_required
def bn_speciales(request):
    """Créer une cotisation spéciale (13/11/2026) : montant juste devant son type ; cibles
    combinables (tous, certains membres, unités, bureaux)."""
    if not _bn(request.user):
        raise PermissionDenied
    from apps.listes.filtres import FiltreListeForm

    filtres = FiltreListeForm(s.NATIONAL, request.POST if request.method == "POST" else None)
    erreur = ""
    if request.method == "POST":
        p = request.POST
        type_montant = p.get("type_montant", TypeMontant.FIXE)
        montant = {
            TypeMontant.FIXE: _entier_ou_none(p.get("montant_fixe")),
            TypeMontant.MINIMUM: _entier_ou_none(p.get("montant_minimum")),
        }.get(type_montant)
        criteres = {}
        if p.get("certains") and p.get("par_criteres"):
            for cle in CRITERES:
                valeurs = [v for v in p.getlist(cle) if v]
                if valeurs:
                    criteres[cle] = valeurs if cle == "grade" else valeurs[0]
        pour_membres = (
            PourMembres.TOUS
            if p.get("tous")
            else PourMembres.CERTAINS
            if p.get("certains")
            else PourMembres.AUCUN
        )
        try:
            echeance = (
                datetime.date.fromisoformat(p.get("echeance", "")) if p.get("echeance") else None
            )
            cs = s.creer_cotisation_speciale(
                libelle=p.get("libelle", ""),
                description=p.get("description", ""),
                echeance=echeance,
                type_montant=type_montant,
                montant=montant,
                montant_suggere=_entier_ou_none(p.get("montant_suggere")),
                pour_membres=pour_membres,
                criteres=criteres,
                membres_des_bureaux=p.getlist("membres_des_bureaux") if p.get("certains") else [],
                membres_designes=p.getlist("membres") if p.get("certains") else [],
                pour_unites=p.getlist("unites"),
                pour_bureaux=p.getlist("bureaux"),
                par=request.user,
            )
        except (s.TresorerieRefusee, ValueError) as e:
            erreur = str(e) if isinstance(e, s.TresorerieRefusee) else "Date d'échéance invalide."
        else:
            messages.success(
                request,
                "Cotisation spéciale créée : elle apparaît « en attente » chez les concernés.",
            )
            return redirect("tresorerie:bn_speciale", pk=cs.pk)
    return render(
        request,
        "tresorerie/bn_speciales.html",
        {
            "erreur": erreur,
            "donnees": request.POST if request.method == "POST" else {},
            "filtres": [filtres[n] for n in CRITERES if n in filtres.fields],
            "liste": CotisationSpeciale.objects.filter(sanction__isnull=True),
            "TypeMontant": TypeMontant,
            "niveaux": s.NIVEAUX_BUREAUX,
            "niveaux_mandats": [
                ("paroisse", "Bureaux d'unité paroissiale"),
                ("circuit", "Bureaux de section circuit"),
                ("region", "Bureaux d'unité régionale de coordination"),
                ("national", "Bureau national"),
            ],
        },
    )


@login_required
def bn_speciale(request, pk):
    if not (_bn(request.user) or est_tresorier_national(request.user)):
        raise PermissionDenied
    cs = get_object_or_404(CotisationSpeciale, pk=pk)
    if request.method == "POST" and _bn(request.user):
        cs.ouverte = not cs.ouverte  # clôture ou réouverture (rien ne s'efface)
        cs.save(update_fields=["ouverte"])
        return redirect("tresorerie:bn_speciale", pk=cs.pk)
    contributions = cs.contributions.select_related("membre").order_by("-date")
    concernes = s.membres_concernes(cs).count()
    payeurs = cs.contributions.exclude(membre=None).values("membre").distinct().count()
    return render(
        request,
        "tresorerie/bn_speciale.html",
        {
            "cs": cs,
            "contributions": contributions[:200],
            "total": sum(c.montant for c in contributions),
            "concernes": concernes,
            "payeurs": payeurs,
            "bureaux": [lib for n, lib in s.NIVEAUX_BUREAUX if n in cs.pour_bureaux],
        },
    )


@login_required
def bn_numeros(request):
    if not _bn(request.user):
        raise PermissionDenied
    from apps.organisation.models import Circuit, Paroisse, Region

    if request.method == "POST":
        unite = s.unite_par_cle(request.POST.get("cle", ""))
        if unite is None:
            raise Http404
        try:
            s.enregistrer_numero(
                unite,
                numero=request.POST.get("numero", ""),
                titulaire=request.POST.get("titulaire", ""),
                par=request.user,
            )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Numéro de {unite.libelle} enregistré.")
        return redirect(f"{request.path}?q={request.POST.get('q', '')}")
    q = request.GET.get("q", "").strip()
    unites = (
        [Unite(Niveau.REGION, r) for r in Region.objects.filter(active=True).order_by("code")]
        + [Unite(Niveau.CIRCUIT, c) for c in Circuit.objects.filter(active=True).order_by("nom")]
        + [Unite(Niveau.PAROISSE, p) for p in Paroisse.objects.filter(active=True).order_by("nom")]
    )
    if q:
        unites = [u for u in unites if q.lower() in u.libelle.lower()]
    numeros = {n.cle: n for n in NumeroMobileMoney.objects.all()}
    return render(
        request,
        "tresorerie/bn_numeros.html",
        {"lignes": [(u, numeros.get(u.cle)) for u in unites], "q": q},
    )


def _mois_param(valeur) -> datetime.date:
    try:
        annee, mois = (int(x) for x in (valeur or "").split("-"))
        return datetime.date(annee, mois, 1)
    except (TypeError, ValueError):
        jour = timezone.localdate().replace(day=1)
        return (jour - datetime.timedelta(days=1)).replace(day=1)  # le mois dernier


@login_required
def bn_reversements(request):
    tresorier, validateur = (
        est_tresorier_national(request.user),
        est_validateur_reversements(request.user),
    )
    if not (tresorier or validateur or _bn(request.user)):
        raise PermissionDenied
    mois = _mois_param(request.GET.get("mois") or request.POST.get("mois"))
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "preparer" and tresorier:
                n = len(s.preparer_reversements(mois, par=request.user))
                messages.success(request, f"État préparé : {n} reversement(s).")
            elif action == "valider" and validateur:
                n = s.valider_reversements(mois, par=request.user)
                messages.success(request, f"{n} reversement(s) validé(s).")
            elif action == "envoye" and tresorier:
                r = get_object_or_404(Reversement, pk=_entier(request.POST.get("reversement")))
                s.marquer_envoye(r, reference=request.POST.get("reference", ""), par=request.user)
                messages.success(request, f"Envoi à {r.libelle} enregistré.")
            else:
                raise PermissionDenied
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        return redirect(f"{request.path}?mois={mois:%Y-%m}")
    reversements = list(Reversement.objects.filter(mois=mois, montant__gt=0))
    apercu = s.parts_du_mois(mois)
    for cle, ligne in apercu.items():
        ligne["numero"] = s.numero_de(cle)
    etats = {r.etat for r in reversements}
    termine = mois < timezone.localdate().replace(day=1)
    if not termine:
        etape, message = (
            0,
            "Ce mois n'est pas encore terminé : on prépare les reversements d'un mois fini.",
        )
    elif not apercu and not reversements:
        etape, message = (
            0,
            "Rien à reverser pour ce mois : aucune cotisation payée par mobile money.",
        )
    elif not reversements:
        etape, message = 1, "En attente de préparation par le Trésorier national."
    elif EtatReversement.PREPARE in etats:
        etape, message = 2, "En attente de validation par le Président ou le Secrétaire national."
    elif EtatReversement.VALIDE in etats:
        etape, message = 3, "Validé : envois à faire par le Trésorier national."
    else:
        etape, message = 4, "Tous les reversements de ce mois sont envoyés."
    return render(
        request,
        "tresorerie/bn_reversements.html",
        {
            "mois": mois,
            "reversements": reversements,
            "total": sum(r.montant for r in reversements),
            "apercu": apercu,
            "total_apercu": sum(x["montant"] for x in apercu.values()),
            "termine": termine,
            "etape": etape,
            "message": message,
            "a_preparer": apercu,
            "tresorier": tresorier,
            "validateur": validateur,
            "Etat": EtatReversement,
        },
    )
