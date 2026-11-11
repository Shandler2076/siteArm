"""Lecture d'un fichier .env (NOM=valeur) : utile chez les hébergeurs où les commandes
(migrations, tâche quotidienne) ne reçoivent pas les variables du site web.
Les variables déjà présentes dans l'environnement gardent la priorité."""

import os
from pathlib import Path


def charger_env(chemin: Path | str) -> list[str]:
    chemin = Path(chemin)
    if not chemin.is_file():
        return []
    lus = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        nom, _, valeur = ligne.partition("=")
        nom, valeur = nom.strip(), valeur.strip()
        if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in "\"'":
            valeur = valeur[1:-1]
        if nom and nom not in os.environ:
            os.environ[nom] = valeur
            lus.append(nom)
    return lus
