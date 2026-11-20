"""Page publique du code QR de la fiche d'identification (authenticité, 20/11/2026).

Sans connexion. Le strict minimum (décision du 20/11/2026) : authentique ou non, matricule,
statut, numéro et date d'émission de la fiche. Ni le nom, ni la photo, ni le téléphone,
ni la date de naissance.
"""

from django.shortcuts import render

from apps.membres.authenticite import etat_fiche, fiche_par_jeton


def verifier_fiche(request, jeton):
    fiche = fiche_par_jeton(jeton)
    etat, raison = etat_fiche(fiche)
    reponse = render(
        request,
        "membres/verifier_fiche.html",
        {
            "fiche": fiche,
            "etat": etat,
            "raison": raison,
            "authentique": etat == "authentique",
            "actif": fiche is not None and fiche.membre.statut == "actif",
        },
    )
    reponse["Cache-Control"] = "no-store"
    reponse["X-Robots-Tag"] = "noindex"
    return reponse
