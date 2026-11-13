"""« Vérifier un membre » hors de son périmètre (décision du mainteneur du 13/11/2026).

Exception encadrée à la règle du gardien des périmètres :
- seulement le Chef et le Secrétaire d'un bureau de paroisse, de circuit ou de région
  (`perimetre.unites_verification`) ;
- par le matricule EXACT, jamais par le nom ;
- un motif obligatoire, inscrit au journal avec l'auteur et le bureau ;
- une carte réduite : photo validée, grade, prénoms et NOM, matricule, statut, catégorie,
  paroisse / circuit / région actuels et le contact de sa paroisse (Secrétaire paroissial).
  Ni téléphone ni adresse du membre, jamais le NPI ni la photo du CIP.
"""

import base64
from dataclasses import dataclass

MOTIFS = [
    ("visite", "Membre en visite dans notre paroisse / notre unité"),
    ("faute", "Faute commise"),
    ("controle", "Contrôle lors d'une activité"),
    ("autre", "Autre motif (à préciser)"),
]


@dataclass
class Carte:
    matricule: str
    nom_complet: str
    statut: str
    categorie: str
    paroisse: str
    circuit: str
    region: str
    photo: str  # data URI de la photo d'identité validée, ou ""
    contact_paroisse: list  # [(nom complet du secrétaire, téléphone)]


def _photo_validee(membre) -> str:
    from apps.membres.models import EtatPhoto

    photo = membre.photos.filter(etat=EtatPhoto.ACCEPTEE).order_by("-pk").first()
    if photo is None or not photo.fichier:
        return ""
    try:
        with photo.fichier.open("rb") as f:
            contenu = f.read()
    except OSError:
        return ""
    nom = photo.fichier.name.lower()
    type_mime = "image/png" if nom.endswith(".png") else "image/jpeg"
    return f"data:{type_mime};base64,{base64.b64encode(contenu).decode()}"


def carte_de(matricule: str) -> Carte | None:
    from apps.bureaux.perimetre import Niveau, Unite, secretaires
    from apps.membres.models import Membre

    membre = (
        Membre.objects.filter(matricule=(matricule or "").strip().upper())
        .select_related("paroisse_integration")
        .first()
    )
    if membre is None:
        return None
    a = membre.affectation_actuelle
    contact = []
    if a is not None:
        for compte in secretaires(Unite(Niveau.PAROISSE, a.paroisse)).select_related("membre"):
            m = getattr(compte, "membre", None)
            if m is not None:
                contact.append((m.nom_complet, m.telephone))
    return Carte(
        matricule=membre.matricule,
        nom_complet=membre.nom_complet,
        statut=membre.get_statut_display(),
        categorie=membre.get_categorie_display(),
        paroisse=a.paroisse.nom if a else "—",
        circuit=a.paroisse.circuit.nom if a else "—",
        region=a.paroisse.circuit.region.nom if a else "—",
        photo=_photo_validee(membre),
        contact_paroisse=contact,
    )
