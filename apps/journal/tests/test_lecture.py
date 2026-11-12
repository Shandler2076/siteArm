"""Journal lisible : chaque ligne est une phrase en français (demande du mainteneur)."""

from html import unescape

from apps.journal import models as j
from apps.journal.lecture import lire
from apps.journal.models import EntreeJournal
from apps.membres.models import Membre


def _entree(action, unite="", auteur=None, **details):
    return EntreeJournal(action=action, unite=unite, auteur=auteur, details=details)


def test_enregistrement_nomme_le_membre_concerne(monde):
    m = monde["m1"]
    (ligne,) = lire([_entree(j.ENREGISTREMENT, membre=m.matricule)])
    assert ligne.texte == f"A enregistré le membre Camarade Test ADJOVI ({m.matricule})."
    assert ligne.unite == "Bureau national"


def test_promotion_de_grade_lisible(monde):
    m = monde["m1"]
    e = _entree(
        j.GRADE_PROMOTION,
        membre=m.matricule,
        grade="Soldat de 3ᵉ classe",
        mode="premiere_consecration",
    )
    (ligne,) = lire([e])
    assert "premiere_consecration" not in ligne.texte
    assert ligne.texte == (
        f"A fait passer Camarade Test ADJOVI ({m.matricule}) au grade de Soldat de 3ᵉ classe "
        "(première consécration)."
    )


def test_unite_ecrite_en_toutes_lettres(monde):
    cle = f"paroisse-{monde['P1'].pk}"
    (ligne,) = lire([_entree(j.CONSULTATION_FICHE, unite=cle, membre=monde["m1"].matricule)])
    assert ligne.unite == "Paroisse P1"
    assert ligne.texte.startswith("A consulté la fiche de Camarade Test ADJOVI")


def test_signalement_et_sanction(monde):
    m = monde["m2"]
    lignes = lire(
        [
            _entree(j.SIGNALEMENT, unite="national", type="deces", membre=m.matricule),
            _entree(
                j.SANCTION,
                membre=m.matricule,
                type="suspension",
                degre=2,
                date_debut="2026-11-01",
                date_fin="2026-11-10",
                reference="D-12",
            ),
            _entree(j.FIN_SANCTION, membre=m.matricule, avant="sanctionne", apres="actif"),
        ]
    )
    assert lignes[0].texte == f"A signalé : Décès de Camarade Test BIO ({m.matricule})."
    assert "Suspension temporaire de service" in lignes[1].texte
    assert "du 01/11/2026 au 10/11/2026" in lignes[1].texte and "D-12" in lignes[1].texte
    assert lignes[2].texte.startswith("Fin de la sanction de Camarade Test BIO")
    assert lignes[2].auteur == "Le site (tâche automatique)"


def test_connexions_et_double_verification(monde):
    lignes = lire(
        [
            _entree(j.CONNEXION, auteur=monde["m1"].compte),
            _entree(j.CONNEXION_ECHOUEE, identifiant="2015-99AS-0001"),
            _entree(
                j.DOUBLE_VERIFICATION, auteur=monde["m1"].compte, evenement="code_faux", essai=2
            ),
        ]
    )
    assert lignes[0].texte == "S'est connecté au site."
    assert lignes[0].auteur == "Camarade Test ADJOVI"
    assert (
        lignes[1].texte == "Tentative de connexion refusée avec l'identifiant « 2015-99AS-0001 »."
    )
    assert lignes[1].auteur == "Inconnu"
    assert lignes[2].texte == "A saisi un code de double vérification faux (essai n° 2)."


def test_membre_inconnu_garde_le_matricule(db):
    (ligne,) = lire([_entree(j.ENREGISTREMENT, membre="2015-01AS-0999")])
    assert ligne.texte == "A enregistré le membre 2015-01AS-0999."


def test_action_inconnue_ne_casse_rien(db):
    (ligne,) = lire([_entree("action_future", cle="valeur")])
    assert ligne.texte == "action_future"


def test_page_journal_affiche_des_phrases(monde, client_technique):
    from apps.journal.services import journaliser

    journaliser(None, j.ENREGISTREMENT, membre=monde["m1"].matricule)
    html = unescape(client_technique.get("/journal/").content.decode())
    assert f"A enregistré le membre Camarade Test ADJOVI ({monde['m1'].matricule})." in html
    assert "Ce qui a été fait" in html
    assert Membre.objects.exists()
