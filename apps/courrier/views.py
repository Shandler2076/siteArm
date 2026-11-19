"""Pages du courrier. Les droits viennent du gardien des périmètres (`unites_courrier`,
`membres_visibles`, `qualite_signataire`) et de `services.peut_voir`."""

import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from apps.bureaux.perimetre import (
    Niveau,
    membres_visibles,
    peut_deposer_signature,
    unite_par_cle,
    unites_courrier,
)
from apps.courrier import services
from apps.courrier.models import (
    TAILLES,
    Courrier,
    Destinataire,
    Etat,
    Langue,
    Mode,
    MotClavier,
    Nature,
    OrigineMot,
    PieceJointe,
    Police,
    ReglagesClavier,
    TypeDestinataire,
)
from apps.securite.services import double_verification_active

NIVEAUX = [
    (Niveau.REGION, "Tous les bureaux régionaux de coordination"),
    (Niveau.CIRCUIT, "Tous les bureaux de section circuit"),
    (Niveau.PAROISSE, "Tous les bureaux d'unité paroissiale"),
]


def _unite(request, cle):
    """Bureau dont le compte tient le courrier ; sinon 404 (même pour le BN)."""
    unite = unite_par_cle(cle)
    if unite is None or unite not in unites_courrier(request.user):
        raise Http404
    return unite


def _gerer_membres(request):
    if not request.user.has_perm("membres.gerer_membres"):
        raise Http404


def _clavier():
    return {"lettres": ReglagesClavier.courant().liste()}


@login_required
def recus(request, cle):
    unite = _unite(request, cle)
    courriers = list(services.courriers_recus(unite)[:200])
    lignes = {
        d.courrier_id: d
        for d in Destinataire.objects.filter(
            courrier__in=courriers, type=TypeDestinataire.BUREAU, unite_cle=unite.cle
        )
    }
    services.marquer_recus(lignes.values(), request.user)  # accusé de réception
    return render(
        request,
        "courrier/recus.html",
        {"unite": unite, "lignes": [(c, lignes.get(c.pk)) for c in courriers]},
    )


@login_required
def envoyes(request, cle):
    unite = _unite(request, cle)
    courriers = services.courriers_envoyes(unite).annotate(
        nb_destinataires=Count("destinataires", filter=Q(destinataires__transmis_par=""))
    )[:300]
    return render(request, "courrier/envoyes.html", {"unite": unite, "courriers": courriers})


def _presentation_contexte() -> dict:
    from apps.courrier.models import POLICE_PAR_LANGUE

    return {
        "langues": Langue.choices,
        "polices": Police.choices,
        "tailles": TAILLES,
        "police_par_langue": {k: v for k, v in POLICE_PAR_LANGUE.items()},
    }


@login_required
def en_correction(request, cle):
    unite = _unite(request, cle)
    courriers = services.courriers_envoyes(unite).filter(etat=Etat.A_CORRIGER)
    return render(request, "courrier/en_correction.html", {"unite": unite, "courriers": courriers})


@login_required
def abandonnes(request, cle):
    unite = _unite(request, cle)
    courriers = services.courriers_envoyes(unite).filter(etat=Etat.ANNULE)
    return render(
        request,
        "courrier/abandonnes.html",
        {"unite": unite, "courriers": courriers, "jours": services.DUREE_ABANDON_JOURS},
    )


def _entiers(valeurs) -> list[int]:
    return [int(v) for v in valeurs if str(v).isdigit()]


def _donnees_formulaire(request, unite) -> dict:
    """Champs du formulaire « Nouveau courrier » (mêmes pour la préparation et l'aperçu)."""
    return {
        "nature": request.POST.get("nature", ""),
        "titre": request.POST.get("titre", ""),
        "mode": request.POST.get("mode", Mode.REDIGE),
        "objet": request.POST.get("objet", ""),
        "texte": request.POST.get("texte", ""),
        "lieu": request.POST.get("lieu", ""),
        "langue": request.POST.get("langue", Langue.FRANCAIS),
        "adresse": request.POST.get("adresse", ""),
        "police": request.POST.get("police", ""),
        "taille": request.POST.get("taille", 12),
        "une_page": bool(request.POST.get("une_page")),
        "bureaux": request.POST.getlist("bureaux"),
        "niveaux": request.POST.getlist("niveaux"),
        "membres": list(
            membres_visibles(unite).filter(pk__in=_entiers(request.POST.getlist("membres")))
        ),
    }


@login_required
def nouveau(request, cle):
    unite = _unite(request, cle)
    annee = timezone.localdate().year
    proposes = services.bureaux_proposes(unite)
    donnees = request.POST if request.method == "POST" else {}
    membres = []
    if request.method == "POST":
        champs = _donnees_formulaire(request, unite)
        membres = champs["membres"]
        try:
            c = services.preparer(
                unite=unite,
                fichier=request.FILES.get("fichier"),
                pieces=request.FILES.getlist("pieces"),
                par=request.user,
                **champs,
            )
        except services.CourrierRefuse as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Courrier préparé : il attend la signature.")
            return redirect("courrier:detail", c.pk)
    choisis = set(request.POST.getlist("bureaux")) if donnees else set()
    return render(
        request,
        "courrier/nouveau.html",
        {
            "unite": unite,
            "bureaux_proposes": [{"cle": u.cle, "libelle": _libelle_choix(u)} for u in proposes],
            "bureaux_choisis": [
                {"cle": u.cle, "libelle": _libelle_choix(u)} for u in proposes if u.cle in choisis
            ],
            "niveaux": NIVEAUX if unite.niveau != Niveau.PAROISSE else [],
            "apercu_numero": services.numero_complet(
                unite, services.proposer_numero(unite, annee), annee
            ),
            "lieu": services.lieu_par_defaut(unite),
            "d": donnees,
            "niveaux_choisis": set(request.POST.getlist("niveaux")) if donnees else set(),
            "membres_choisis": membres,
            "clavier": _clavier(),
            "Nature": Nature,
            "url_apercu": reverse("courrier:apercu", args=[unite.cle]),
            "url_apercu_pdf": reverse("courrier:apercu_pdf", args=[unite.cle]),
            **_presentation_contexte(),
        },
    )


def _libelle_choix(u) -> str:
    return "Bureau National de Commandement" if u.niveau == Niveau.NATIONAL else u.libelle


def _rendu_apercu(request, c) -> HttpResponse:
    from apps.courrier.pdf import LIGNES_FIXES

    unite = services.unite_expeditrice(c)
    return render(
        request,
        "courrier/_apercu.html",
        {
            "c": c,
            "ligne_bureau": services.ligne_bureau(unite) if unite else "",
            "lignes_fixes": LIGNES_FIXES,
            "texte": mark_safe(services.texte_html(c.texte)),  # échappé par texte_html
            "famille": FAMILLES_APERCU.get(c.police, "serif"),
        },
    )


FAMILLES_APERCU = {
    "liberation_serif": "CourrierLiberationSerif",
    "liberation_sans": "CourrierLiberationSans",
    "charis": "CourrierCharis",
    "gentium": "CourrierGentium",
    "noto_serif": "CourrierNotoSerif",
}


def _pdf_apercu(c) -> HttpResponse:
    from apps.courrier.pdf import courrier_pdf

    r = HttpResponse(courrier_pdf(c, avec_membres=False), content_type="application/pdf")
    r["Content-Disposition"] = 'inline; filename="apercu-courrier.pdf"'
    r["Cache-Control"] = "private, no-store"
    return r


def _erreur_apercu(request, message) -> HttpResponse:
    return render(request, "courrier/_apercu_erreur.html", {"message": message})


@login_required
@require_POST
def apercu(request, cle, en_pdf=False):
    """Aperçu du nouveau courrier, sans rien enregistrer (décision du 18/11/2026)."""
    unite = _unite(request, cle)
    try:
        c = services.apercu(unite=unite, par=request.user, **_donnees_formulaire(request, unite))
    except services.CourrierRefuse as e:
        return _erreur_apercu(request, str(e))
    return _pdf_apercu(c) if en_pdf else _rendu_apercu(request, c)


@login_required
@require_POST
def apercu_modification(request, pk, en_pdf=False):
    """Aperçu d'un courrier en correction, avec les modifications non encore enregistrées."""
    c = _courrier_visible(request, pk)
    unite = services.unite_expeditrice(c)
    if unite is None or unite not in unites_courrier(request.user):
        raise Http404
    try:
        apercu_c = services.apercu_modification(
            c,
            par=request.user,
            objet=request.POST.get("objet", ""),
            texte=request.POST.get("texte", ""),
            lieu=request.POST.get("lieu", ""),
            adresse=request.POST.get("adresse", ""),
            titre=request.POST.get("titre"),
            langue=request.POST.get("langue") or None,
            police=request.POST.get("police") or None,
            taille=request.POST.get("taille") or None,
            une_page=bool(request.POST.get("une_page")),
        )
    except services.CourrierRefuse as e:
        return _erreur_apercu(request, str(e))
    return _pdf_apercu(apercu_c) if en_pdf else _rendu_apercu(request, apercu_c)


@login_required
def mots(request):
    """Mots proposés par le clavier goun pendant la frappe (rédacteurs de courrier seulement)."""
    if not (unites_courrier(request.user) or request.user.has_perm("membres.gerer_membres")):
        raise Http404
    r = JsonResponse({"mots": services.proposer_mots(request.GET.get("debut", "")[:60])})
    r["Cache-Control"] = "private, max-age=600"
    return r


@login_required
def recherche(request, cle):
    """Recherche d'un membre du périmètre du bureau (matricule ou nom), réponse JSON."""
    from django.db.models import Q

    unite = _unite(request, cle)
    texte = request.GET.get("q", "").strip()
    resultats = []
    if len(texte) >= 2:
        filtre = Q()
        for mot in texte.split():
            filtre &= Q(nom__icontains=mot) | Q(prenoms__icontains=mot)
        membres = (
            membres_visibles(unite)
            .filter(Q(matricule__icontains=texte) | filtre)
            .exclude(statut__in=services.SORTIS)
            .order_by("nom", "prenoms")[:20]
        )
        resultats = [{"pk": m.pk, "nom": m.nom_complet, "matricule": m.matricule} for m in membres]
    return JsonResponse({"resultats": resultats})


def vue_complete(request, c: Courrier) -> bool:
    """Seul l'expéditeur voit les noms de tous les destinataires et leur suivi."""
    unite = services.unite_expeditrice(c)
    return unite is not None and unite in unites_courrier(request.user)


def _rubrique(request, c: Courrier, mes_lignes=()) -> str | None:
    """Rubrique du menu à marquer sur les pages d'un courrier (on sait toujours où l'on est)."""
    unite = services.unite_expeditrice(c)
    signe = c.etat == Etat.A_SIGNER and services.peut_signer(request.user, c)
    if signe:
        return reverse("courrier:a_signer")
    if unite is not None and unite in unites_courrier(request.user):
        nom = {
            Etat.A_CORRIGER: "courrier:en_correction",
            Etat.ANNULE: "courrier:abandonnes",
        }.get(c.etat, "courrier:envoyes")
        return reverse(nom, args=[unite.cle])
    for d in mes_lignes:
        if d.type == TypeDestinataire.BUREAU:
            return reverse("courrier:recus", args=[d.unite_cle])
    return reverse("courrier:moi") if mes_lignes else None


def _courrier_visible(request, pk) -> Courrier:
    c = get_object_or_404(Courrier, pk=pk)
    if not services.peut_voir(request.user, c):
        raise Http404
    return c


@login_required
def detail(request, pk):
    c = _courrier_visible(request, pk)
    mes_lignes = services.destinataires_du_compte(request.user, c)
    for d in mes_lignes:
        services.ouvrir(d, request.user)  # accusé de lecture
    unite = services.unite_expeditrice(c)
    expediteur = unite is not None and unite in unites_courrier(request.user)
    voit_suivi = vue_complete(request, c)
    request.rubrique_menu = _rubrique(request, c, mes_lignes)
    transmis = (
        c.destinataires.exclude(transmis_par="")
        .values("transmis_par")
        .annotate(n=Count("pk"), lus=Count("lu_le"))
        .order_by("transmis_par")
        if voit_suivi
        else []
    )
    paroisses = [
        u
        for u in unites_courrier(request.user)
        if u.niveau == Niveau.PAROISSE
        and any(d.type == "bureau" and d.unite_cle == u.cle for d in mes_lignes)
    ]
    return render(
        request,
        "courrier/detail.html",
        {
            "c": c,
            "mes_lignes": [Destinataire.objects.get(pk=d.pk) for d in mes_lignes],
            "expediteur": expediteur,
            "suivi": list(services.destinataires_directs(c).select_related("lu_par", "accuse_par"))
            if voit_suivi
            else [],
            "transmis": [(unite_par_cle(t["transmis_par"]), t["n"], t["lus"]) for t in transmis],
            "qualite": services.peut_signer(request.user, c),
            "a_signature": services.signature_active(request.user) is not None,
            "transmettre": paroisses if c.communique and c.envoye else [],
            "texte_html": mark_safe(services.texte_html(c.texte)),  # échappé par texte_html
            "destinataire_texte": services.libelle_destinataires(
                c, avec_membres=voit_suivi, membre=getattr(request.user, "membre", None)
            ),
        },
    )


@login_required
@require_POST
def action(request, pk):
    c = _courrier_visible(request, pk)
    quoi = request.POST.get("action", "")
    try:
        if quoi == "valider":
            version = request.POST.get("version", "")
            services.valider(c, par=request.user, version=int(version) if version.isdigit() else -1)
            messages.success(request, "Courrier signé et envoyé.")
        elif quoi == "renvoyer":
            services.renvoyer(c, motif=request.POST.get("motif", ""), par=request.user)
            messages.success(request, "Correction demandée au secrétaire.")
        elif quoi == "corriger":
            services.mettre_en_correction(c, par=request.user)
            return redirect("courrier:modifier", c.pk)
        elif quoi == "soumettre":
            services.soumettre_a_la_signature(c, par=request.user)
            messages.success(request, "Courrier soumis à la signature.")
        elif quoi == "reprendre":
            services.reprendre(c, par=request.user)
            messages.success(request, "Courrier repris : il est en correction.")
            return redirect("courrier:modifier", c.pk)
        elif quoi == "supprimer":
            cle = c.expediteur_cle
            services.supprimer(c, par=request.user)
            messages.success(request, "Courrier supprimé.")
            return redirect("courrier:abandonnes", cle)
        elif quoi == "abandonner":
            services.annuler(c, par=request.user)
            messages.success(request, "Courrier abandonné.")
        elif quoi == "accuser":
            ligne = get_object_or_404(Destinataire, pk=request.POST.get("ligne", ""), courrier=c)
            services.accuser(ligne, par=request.user)
            messages.success(request, "Merci : l'expéditeur voit que vous avez reçu le courrier.")
        elif quoi == "transmettre":
            unite = unite_par_cle(request.POST.get("unite", ""))
            if unite is None:
                raise Http404
            n = services.transmettre_aux_membres(c, unite, par=request.user)
            messages.success(request, f"Communiqué transmis à {n} membre(s).")
        else:
            raise Http404
    except services.CourrierRefuse as e:
        messages.error(request, str(e))
    return redirect("courrier:detail", c.pk)


@login_required
def modifier(request, pk):
    c = _courrier_visible(request, pk)
    unite = services.unite_expeditrice(c)
    if unite is None or unite not in unites_courrier(request.user):
        raise Http404
    if c.etat != Etat.A_CORRIGER:  # « Modifier » met d'abord le courrier en correction
        return redirect("courrier:detail", c.pk)
    request.rubrique_menu = reverse("courrier:en_correction", args=[unite.cle])
    if request.method == "POST":
        soumettre = "soumettre" in request.POST
        try:
            services.modifier(
                c,
                objet=request.POST.get("objet", ""),
                texte=request.POST.get("texte", ""),
                fichier=request.FILES.get("fichier"),
                lieu=request.POST.get("lieu", ""),
                adresse=request.POST.get("adresse", ""),
                titre=request.POST.get("titre"),
                langue=request.POST.get("langue") or None,
                police=request.POST.get("police") or None,
                taille=request.POST.get("taille") or None,
                une_page=bool(request.POST.get("une_page")),
                soumettre=soumettre,
                par=request.user,
            )
        except services.CourrierRefuse as e:
            messages.error(request, str(e))
        else:
            if soumettre:
                messages.success(request, "Courrier corrigé et soumis à la signature.")
                return redirect("courrier:detail", c.pk)
            messages.success(request, "Modifications enregistrées (toujours en correction).")
            return redirect("courrier:modifier", c.pk)
        c.refresh_from_db()
    return render(
        request,
        "courrier/modifier.html",
        {
            "c": c,
            "clavier": _clavier(),
            "url_apercu": reverse("courrier:apercu_modification", args=[c.pk]),
            "url_apercu_pdf": reverse("courrier:apercu_modification_pdf", args=[c.pk]),
            **_presentation_contexte(),
        },
    )


def _fichier(champ, nom):
    if not champ:
        raise Http404
    type_contenu = mimetypes.guess_type(champ.name)[0] or "application/octet-stream"
    r = FileResponse(champ.open("rb"), content_type=type_contenu, filename=nom)
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
def pdf(request, pk):
    from apps.courrier.pdf import courrier_pdf

    c = _courrier_visible(request, pk)
    complet = vue_complete(request, c)
    membre = getattr(request.user, "membre", None)
    r = HttpResponse(
        courrier_pdf(c, avec_membres=complet, membre=membre), content_type="application/pdf"
    )
    nom = f"courrier-{c.annee}-{c.numero_ordre:03d}.pdf"
    r["Content-Disposition"] = f'inline; filename="{nom}"'
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
def original(request, pk):
    c = _courrier_visible(request, pk)
    return _fichier(c.fichier, c.fichier.name.rsplit("/", 1)[-1] if c.fichier else "")


@login_required
def piece(request, pk, piece_pk):
    c = _courrier_visible(request, pk)
    p = get_object_or_404(PieceJointe, pk=piece_pk, courrier=c)
    return _fichier(p.fichier, p.fichier.name.rsplit("/", 1)[-1])


@login_required
def a_signer(request):
    return render(
        request,
        "courrier/a_signer.html",
        {
            "courriers": services.courriers_a_signer(request.user),
            "a_signature": services.signature_active(request.user) is not None,
        },
    )


@login_required
def moi(request):
    membre = getattr(request.user, "membre", None)
    if membre is None:
        raise Http404
    courriers = list(services.courriers_du_membre(membre)[:200])
    return render(request, "courrier/moi.html", {"courriers": courriers})


@login_required
def ma_signature(request):
    if not peut_deposer_signature(request.user):
        raise Http404
    if request.method == "POST":
        fichier = request.FILES.get("image")
        if fichier is None:
            messages.error(request, "Choisissez l'image de votre signature.")
        else:
            try:
                services.deposer_signature(
                    request.user,
                    fichier,
                    mot_de_passe=request.POST.get("mot_de_passe", ""),
                    code=request.POST.get("code", ""),
                )
            except services.CourrierRefuse as e:
                messages.error(request, str(e))
            else:
                messages.success(request, "Votre signature est enregistrée.")
                return redirect("courrier:ma_signature")
    return render(
        request,
        "courrier/ma_signature.html",
        {
            "signature": services.signature_active(request.user),
            "avec_code": double_verification_active(request.user),
        },
    )


@login_required
def ma_signature_image(request):
    """L'image n'est montrée qu'à son propriétaire (pas même au BN)."""
    sig = services.signature_active(request.user)
    if sig is None:
        raise Http404
    return _fichier(sig.image, "signature.png")


def verifier(request, jeton):
    """Page publique ouverte par le QR code : authentique ou non, sans le texte du courrier."""
    if not services.JETON.match(jeton or ""):
        c = None
    else:
        c = Courrier.objects.filter(jeton=jeton, etat=Etat.ENVOYE).first()
    reponse = render(request, "courrier/verifier.html", {"c": c})
    reponse["Cache-Control"] = "no-store"
    reponse["X-Robots-Tag"] = "noindex"
    return reponse


@login_required
def bn_registre(request):
    _gerer_membres(request)
    # Registre du national seulement (décision du 18/11/2026) : courriers envoyés par le BN et
    # courriers adressés au BN. Chaque région, circuit, paroisse tient le sien.
    national = Q(expediteur_cle="national") | Q(
        destinataires__type=TypeDestinataire.BUREAU, destinataires__unite_cle="national"
    )
    courriers = (
        Courrier.objects.filter(national, etat=Etat.ENVOYE)
        .distinct()
        .prefetch_related(
            Prefetch(
                "destinataires",
                queryset=Destinataire.objects.filter(transmis_par="", type=TypeDestinataire.BUREAU),
            )
        )
    )
    bureau = request.GET.get("bureau", "")
    if bureau == "envoyes":
        courriers = courriers.filter(expediteur_cle="national")
    elif bureau == "recus":
        courriers = courriers.exclude(expediteur_cle="national")
    annee = request.GET.get("annee", "")
    if annee.isdigit():
        courriers = courriers.filter(annee=int(annee))
    expediteurs = [("envoyes", "Envoyés par le Bureau national"), ("recus", "Reçus des bureaux")]
    return render(
        request,
        "courrier/bn_registre.html",
        {
            "courriers": courriers.order_by("-date_envoi")[:500],
            "expediteurs": expediteurs,
            "bureau": bureau,
            "annee": annee,
        },
    )


@login_required
def bn_clavier(request):
    _gerer_membres(request)
    if request.method == "POST":
        quoi = request.POST.get("action")
        try:
            if quoi == "lettres":
                services.enregistrer_lettres(request.POST.get("lettres", ""), par=request.user)
                messages.success(request, "Lettres du clavier enregistrées.")
            elif quoi == "mots":
                n = services.enregistrer_mots_bn(request.POST.get("mots", ""), par=request.user)
                messages.success(request, f"{n} mot(s) enregistré(s).")
            elif quoi == "masquer":
                services.masquer_mot(request.POST.get("mot", ""), par=request.user)
                messages.success(request, "Mot retiré des propositions.")
        except services.CourrierRefuse as e:
            messages.error(request, str(e))
        return redirect("courrier:bn_clavier")
    return render(
        request,
        "courrier/bn_clavier.html",
        {
            "lettres": ReglagesClavier.courant().lettres,
            "mots_bn": "\n".join(
                MotClavier.objects.filter(origine=OrigineMot.BN, actif=True)
                .order_by("mot")
                .values_list("mot", flat=True)
            ),
            "appris": services.mots_appris_proposes(),
            "nb_lexique": MotClavier.objects.filter(origine=OrigineMot.LEXIQUE, actif=True).count(),
            "clavier": _clavier(),
        },
    )
