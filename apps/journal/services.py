from apps.journal.models import EntreeJournal


def journaliser(par, action: str, unite: str = "", **details) -> EntreeJournal:
    auteur = par if getattr(par, "is_authenticated", False) else None
    return EntreeJournal.objects.create(
        auteur=auteur,
        auteur_identifiant=getattr(auteur, "identifiant", "") if auteur else "",
        action=action,
        unite=unite,
        details=details,
    )
