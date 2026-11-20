"""Les blocs d'un événement (décisions du 20/11/2026), dans l'ordre de la page de convocation :
bureau d'organisation et supervision (d'office), puis les sections (créées à la main) — ou
« Participants » pour un événement sans section —, puis les invitations d'honneur."""

from apps.evenements.models import Role

BUREAU, SUPERVISION, HONNEUR, PARTICIPANTS = "bureau", "supervision", "honneur", "participants"
ROLES_FIXES = {
    BUREAU: Role.BUREAU_ORGANISATION,
    SUPERVISION: Role.SUPERVISEUR,
    HONNEUR: Role.INVITE_HONNEUR,
    PARTICIPANTS: Role.PARTICIPANT,
}


def cle_bloc(c) -> str:
    """Le bloc d'une convocation."""
    if c.role in (Role.BUREAU_ORGANISATION, "bureau"):
        return BUREAU
    if c.role == Role.SUPERVISEUR:
        return SUPERVISION
    if c.role == Role.INVITE_HONNEUR:
        return HONNEUR
    if c.session_id:
        return f"section-{c.session_id}"
    return PARTICIPANTS


def blocs(ev) -> list[dict]:
    """[{cle, titre, nombre}] dans l'ordre d'affichage, avec le nombre de convoqués."""
    sessions = list(ev.sessions.all())
    nombres: dict = {}
    for c in ev.convocations.filter(active=True):
        nombres[cle_bloc(c)] = nombres.get(cle_bloc(c), 0) + 1
    liste = [(BUREAU, "Bureau d'organisation"), (SUPERVISION, "Supervision")]
    liste += [(f"section-{s.pk}", s.nom) for s in sessions]
    # « Participants » : événement sans section, ou anciennes convocations hors section (officiel,
    # autre…) qui doivent rester visibles et retirables.
    if not sessions or nombres.get(PARTICIPANTS):
        liste.append((PARTICIPANTS, "Participants"))
    liste.append((HONNEUR, "Invitations d'honneur"))
    return [{"cle": cle, "titre": titre, "nombre": nombres.get(cle, 0)} for cle, titre in liste]


def convocations_du_bloc(ev, cle: str):
    qs = ev.convocations.filter(active=True).select_related("membre", "session")
    return [c for c in qs if cle_bloc(c) == cle]
