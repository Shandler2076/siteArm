"""Colonnes du modèle Excel officiel, dans l'ordre (l'astérisque marque l'obligatoire)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Colonne:
    entete: str
    champ: str
    obligatoire: bool
    # Colonne ajoutée après la première version du modèle : son absence est acceptée.
    entete_facultative: bool = False


COLONNES = [
    Colonne("Nom*", "nom", True),
    Colonne("Prénoms*", "prenoms", True),
    Colonne("Sexe*", "sexe", True),
    Colonne("Date de naissance", "date_naissance", False),
    Colonne("Lieu de naissance", "lieu_naissance", False),
    Colonne("Situation matrimoniale", "situation_matrimoniale", False),
    Colonne("NPI", "npi", False),
    Colonne("Téléphone*", "telephone", True),
    Colonne("WhatsApp", "whatsapp", False),
    Colonne("Email", "email", False),
    Colonne("Quartier", "quartier", False),
    Colonne("Ville", "ville", False),
    Colonne("Profession", "profession", False),
    Colonne("Personne à contacter (nom)", "urgence_nom", False),
    Colonne("Personne à contacter (téléphone)", "urgence_telephone", False),
    Colonne("Année d'intégration*", "annee_integration", True),
    Colonne("Paroisse d'intégration*", "paroisse_integration", True),
    Colonne("Catégorie", "categorie", False),
    Colonne("Grade", "grade", False, entete_facultative=True),
    Colonne("Date du grade", "date_grade", False, entete_facultative=True),
    Colonne("Paroisse actuelle", "paroisse_actuelle", False, entete_facultative=True),
]

PAR_CHAMP = {c.champ: c for c in COLONNES}
