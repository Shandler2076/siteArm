from apps.journal.models import EntreeJournal


def journaliser(par, action: str, unite: str = "", **details) -> EntreeJournal:
    auteur = par if getattr(par, "is_authenticated", False) else None
    return EntreeJournal.objects.create(auteur=auteur, action=action, unite=unite, details=details)
