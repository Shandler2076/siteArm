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
        self._cotisations(hasard, crees, par)
        self._evenements(hasard, crees, par)
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

    def _cotisations(self, hasard, membres, par):
        """Cotisations fictives depuis janvier : à jour, en retard, en attente, refusées."""
        from django.utils import timezone

        from apps.bureaux.models import Mandat
        from apps.cotisations.models import NiveauPart, ParametresCotisations
        from apps.cotisations.regles import situation
        from apps.cotisations.services import (
            CotisationRefusee,
            marquer_part_recue,
            refuser,
            saisir_versement,
            valider,
        )

        jour = timezone.localdate()
        # Saisie par le Secrétaire national, validation par le bureau du circuit de démonstration
        # (celui qui saisit ne valide pas).
        mandat = (
            Mandat.objects.filter(fonction__niveau="circuit", fonction__droit_gerer=True)
            .select_related("membre__compte")
            .first()
        )
        validateur = mandat.membre.compte if mandat else None
        parametres = ParametresCotisations.courant()
        parametres.mois_depart = jour.replace(month=1, day=1)
        parametres.save()
        # Membres fictifs « enregistrés » l'an dernier : tous les mois de l'année sont dus.
        debut = timezone.make_aware(datetime.datetime(jour.year - 1, 6, 1, 9))
        Membre.objects.filter(pk__in=[m.pk for m in membres]).update(date_enregistrement=debut)
        valides = []
        for m in membres:
            m.refresh_from_db()
            dus = len(situation(m, jour.replace(day=1)).dus)
            tirage = hasard.random()
            try:
                if tirage < 0.45:  # à jour, parfois d'avance
                    nb = dus + (1 if hasard.random() < 0.2 and jour.month < 12 else 0)
                    v = saisir_versement(m, montant=100 * nb, date_versement=jour, par=par)
                    valides += valider([v], par=validateur)
                elif tirage < 0.75:  # en retard
                    nb = hasard.randint(1, max(1, dus - 2))
                    v = saisir_versement(m, montant=100 * nb, date_versement=jour, par=par)
                    valides += valider([v], par=validateur)
                elif tirage < 0.85:  # versement en attente de validation
                    v = saisir_versement(
                        m, montant=100 * max(1, dus - 1), date_versement=jour, par=par
                    )
                elif tirage < 0.9:  # versement refusé par le circuit
                    v = saisir_versement(m, montant=100, date_versement=jour, par=par)
                    refuser(v, motif="Montant non reçu (démonstration)", par=par)
            except CotisationRefusee:
                continue
        if valides:
            # Un tiers des versements validés le mois dernier ; la part de l'un est reçue.
            from apps.cotisations.models import Versement

            anciens = [v.pk for v in valides[: max(1, len(valides) // 3)]]
            Versement.objects.filter(pk__in=anciens).update(
                date_validation=timezone.now() - datetime.timedelta(days=35)
            )
            v = Versement.objects.get(pk=anciens[0])
            mois = timezone.localdate(v.date_validation).replace(day=1)
            for niveau in (NiveauPart.CIRCUIT, NiveauPart.REGION):
                marquer_part_recue(
                    niveau=niveau, paroisse=v.paroisse, mois_validation=mois, par=validateur
                )

    def _evenements(self, hasard, membres, par):
        """Un pèlerinage à venir (avec autorisations) et un conclave passé (présences pointées)."""
        from django.utils import timezone

        from apps.evenements.models import Presence
        from apps.evenements.services import convoquer, creer_evenement, pointer

        maintenant = timezone.localtime()
        annee = (
            maintenant.year if maintenant.month < 12 or maintenant.day < 24 else maintenant.year + 1
        )
        nativite = creer_evenement(
            nom=f"Pèlerinage de la Nativité {annee}",
            debut=timezone.make_aware(datetime.datetime(annee, 12, 24, 7, 0)),
            lieu="Porto-Novo",
            description="Fictif (démonstration). Équipes de travail par section.",
            avec_autorisation=True,
            avec_sections=True,
            sessions=["Section Mer", "Section Culte", "Section Fruits"],
            par=par,
        )
        choisis = hasard.sample(membres, min(33, len(membres)))
        sessions = list(nativite.sessions.all())
        for i, session in enumerate(sessions):
            groupe = choisis[i : 30 : 3]
            convoquer(nativite, groupe[:1], session=session, role="superviseur", par=par)
            convoquer(nativite, groupe[1:], session=session, par=par)
        convoquer(nativite, choisis[30:], role="bureau", par=par)
        conclave = creer_evenement(
            nom="Conclave du Bureau national",
            debut=maintenant - datetime.timedelta(days=20),
            lieu="Siège du Bureau national",
            avec_autorisation=False,
            par=par,
        )
        convoques = convoquer(conclave, hasard.sample(membres, min(12, len(membres))), par=par)
        for c in convoques:
            pointer(
                c,
                hasard.choices([Presence.PRESENT, Presence.ABSENT, Presence.EXCUSE], [75, 15, 10])[
                    0
                ],
                par=par,
            )

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
