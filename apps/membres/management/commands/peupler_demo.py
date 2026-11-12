"""Remplit un SITE D'ESSAI avec des membres fictifs, des bureaux et quelques mouvements.

Refuse de s'exécuter si DJANGO_SITE_DEMO n'est pas activé, ou si des membres existent déjà :
il ne doit jamais toucher un vrai site.
"""

import datetime
import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bureaux.models import Fonction, Mandat
from apps.membres.models import Membre
from apps.membres.services import enregistrer_membre, generer_mot_de_passe_provisoire
from apps.organisation.models import Paroisse, Region

NOMS = [
    "AGOSSOU",
    "AHOUANSOU",
    "AKPOVI",
    "ASSOGBA",
    "DOSSOU",
    "GBAGUIDI",
    "HOUNKPATIN",
    "HOUNSOU",
    "KPADONOU",
    "MEDEGAN",
    "SOGLO",
    "TOSSOU",
    "ZINSOU",
    "ADJOVI",
    "BOKO",
    "DJOSSOU",
    "FAGLA",
    "GNONLONFOUN",
    "HOUNGBO",
    "KOUTON",
]
PRENOMS_H = ["Jean", "Paul", "Pierre", "Luc", "Joseph", "Marc", "Albert", "Romaric", "Fiacre"]
PRENOMS_F = ["Marie", "Grâce", "Esther", "Rachelle", "Elise", "Bernadette", "Félicité", "Ruth"]

BUREAUX = [
    ("national", "Président"),
    ("national", "Secrétaire national"),
    ("region", "Coordinateur régional"),
    ("region", "Secrétaire régional"),
    ("circuit", "Chef de Section de Circuit"),
    ("circuit", "Secrétaire de Circuit"),
    ("paroisse", "Chef d'Unité paroissiale"),
    ("paroisse", "Secrétaire paroissial"),
]


class Command(BaseCommand):
    help = "Site d'essai : crée des membres FICTIFS et des comptes de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--membres", type=int, default=150)
        parser.add_argument("--graine", type=int, default=2026)

    def handle(self, *args, membres, graine, **options):
        if not getattr(settings, "SITE_DEMO", False):
            raise CommandError(
                "Refusé : cette commande ne fonctionne que sur un site d'essai "
                "(DJANGO_SITE_DEMO=True)."
            )
        if not Region.objects.exists():
            raise CommandError(
                "Chargez d'abord le territoire : python manage.py charger_territoire"
            )
        if Membre.objects.exists():
            raise CommandError(
                "Il y a déjà des membres : la démonstration n'est créée qu'une fois."
            )
        hasard = random.Random(graine)
        region = Region.objects.filter(active=True).order_by("code").first()
        circuit = region.circuits.filter(active=True).order_by("nom").first()
        paroisse = circuit.paroisses.filter(active=True).order_by("nom").first()
        unites = {"national": None, "region": region, "circuit": circuit, "paroisse": paroisse}
        comptes = []
        with transaction.atomic():
            for niveau, nom_fonction in BUREAUX:
                m = self._membre(hasard, paroisse, None, avec_mot_de_passe=True)
                mot = generer_mot_de_passe_provisoire()
                m.compte.set_password(mot)
                m.compte.doit_changer_mot_de_passe = False
                m.compte.save()
                fonction = Fonction.objects.get(niveau=niveau, nom=nom_fonction)
                mandat = Mandat(
                    membre=m,
                    fonction=fonction,
                    date_debut=datetime.date(2025, 1, 1),
                    **({niveau: unites[niveau]} if unites[niveau] else {}),
                )
                mandat.full_clean()
                mandat.save()
                if niveau == "national":  # des responsables nationaux hauts gradés
                    self._grades(hasard, m, None, nomination=hasard.choice([8, 9]))
                lieu = unites[niveau].nom if unites[niveau] else "national"
                comptes.append((f"{nom_fonction} ({lieu})", m.matricule, mot))
            par = Membre.objects.get(matricule=comptes[1][1]).compte  # Secrétaire national
            paroisses = list(Paroisse.objects.filter(active=True))
            proches = list(Paroisse.objects.filter(circuit__region=region, active=True))
            crees = []
            for i in range(membres):
                lieu = hasard.choice(proches if i % 2 == 0 else paroisses)
                crees.append(self._membre(hasard, lieu, par))
                self._grades(hasard, crees[-1], par)
            simple = crees[0]
            mot = generer_mot_de_passe_provisoire()
            simple.compte.set_password(mot)
            simple.compte.doit_changer_mot_de_passe = False
            simple.compte.save()
            comptes.append(("Membre simple", simple.matricule, mot))
        self._mouvements(hasard, crees, par)
        self.stdout.write(self.style.SUCCESS(f"{Membre.objects.count()} membres fictifs créés."))
        self.stdout.write("\nComptes de démonstration (à noter, ils ne seront plus affichés) :")
        largeur = max(len(r) for r, _, _ in comptes) + 2
        self.stdout.write(f"{'Rôle':<{largeur}}{'Identifiant':<17}Mot de passe")
        for role, identifiant, mot in comptes:
            self.stdout.write(f"{role:<{largeur}}{identifiant:<17}{mot}")
        self.stdout.write(
            "\nLes comptes du Bureau national devront activer la double vérification "
            "(application d'authentification) à leur première connexion."
        )

    def _membre(self, hasard, paroisse, par, avec_mot_de_passe=False):
        sexe = hasard.choice("MF")
        prenoms = hasard.choice(PRENOMS_H if sexe == "M" else PRENOMS_F)
        naissance = None
        if hasard.random() > 0.08:
            naissance = datetime.date(
                hasard.randint(1950, 2012), hasard.randint(1, 12), hasard.randint(1, 28)
            )
        categorie = hasard.choices(["actif", "honneur", "sympathisant"], [85, 5, 10])[0]
        return enregistrer_membre(
            donnees={
                "nom": hasard.choice(NOMS),
                "prenoms": prenoms,
                "sexe": sexe,
                "date_naissance": naissance,
                "telephone": f"019{hasard.randint(0, 9999999):07d}",
                "categorie": categorie,
            },
            paroisse_integration=paroisse,
            annee_integration=hasard.randint(1998, 2025),
            par=par,
            notifier=False,
            avec_mot_de_passe=avec_mot_de_passe,
        ).membre

    def _grades(self, hasard, membre, par, nomination=None):
        """Parcours de grades vraisemblable : première consécration, tests aux durées de
        l'art. 78, parfois une nomination chez les plus anciens."""
        from apps.grades.services import promouvoir
        from apps.membres.grades import DUREES_MINIMALES
        from apps.mouvements.statuts import ajouter_mois

        if nomination is None and hasard.random() < 0.08:
            return  # reste Camarade : pas encore consacré
        aujourdhui = datetime.date.today()
        jour = membre.date_grade
        etapes = []
        jour = ajouter_mois(jour, hasard.randint(3, 15))
        if jour <= aujourdhui:
            etapes.append((1, jour))
            for grade in range(1, 6):
                jour = ajouter_mois(jour, 12 * DUREES_MINIMALES[grade] + hasard.randint(0, 24))
                if jour > aujourdhui or hasard.random() > 0.7:
                    break
                etapes.append((grade + 1, jour))
        if nomination is None and etapes and etapes[-1][0] >= 5 and hasard.random() < 0.35:
            nomination = hasard.choice([7, 7, 7, 8, 9])
        if nomination is not None:
            depart = etapes[-1][1] if etapes else membre.date_grade
            jour = ajouter_mois(depart, hasard.randint(6, 48))
            etapes.append((nomination, min(jour, aujourdhui)))
        for grade, date_effet in etapes:
            promouvoir(
                membre,
                grade=grade,
                date_effet=date_effet,
                reference=f"Décision fictive {date_effet.year}",
                par=par,
            )
            membre.refresh_from_db()

    def _mouvements(self, hasard, membres, par):
        """Quelques situations pour essayer toutes les pages (statuts, mutation, sanction)."""
        from apps.mouvements.sanctions import enregistrer_sanction
        from apps.mouvements.services import demander_mutation, signaler
        from apps.mouvements.statuts import changer_statut

        aujourdhui = datetime.date.today()
        for m in membres[1:4]:
            changer_statut(
                m, "decede", par=par, date_effet=datetime.date(2025, 6, 1), motif="Démonstration"
            )
        enregistrer_sanction(
            membre=membres[4],
            degre=2,
            type="suspension",
            date_debut=aujourdhui,
            date_fin=aujourdhui + datetime.timedelta(days=10),
            motif="Démonstration",
            reference="Décision fictive n° 1",
            par=par,
        )
        autres = list(
            Paroisse.objects.filter(active=True).exclude(
                pk=membres[5].affectation_actuelle.paroisse_id
            )[:1]
        )
        if autres:
            demander_mutation(membre=membres[5], paroisse_arrivee=autres[0], par=par)
        signaler(
            membre=membres[6],
            type="categorie",
            par=par,
            unite="national",
            nouvelle_categorie="honneur" if membres[6].categorie != "honneur" else "actif",
        )
