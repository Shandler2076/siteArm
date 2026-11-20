"""Les droits du Bureau National de Commandement viennent des mandats (et non d'autorisations
manuelles) : `perimetre.droits_nationaux` (cases de « Fonctions et droits » + droits en dur du
Président et du Secrétaire national)."""

from apps.bureaux.perimetre import droits_nationaux

PERMISSIONS_BN = frozenset({"membres.gerer_membres", "membres.voir_cip"})


class MandatBackend:
    def authenticate(self, request, **kwargs):
        return None

    def get_user(self, user_id):
        return None

    def get_all_permissions(self, user, obj=None) -> set[str]:
        if not getattr(user, "is_active", False) or obj is not None:
            return set()
        if not hasattr(user, "_permissions_mandat"):
            user._permissions_mandat = droits_nationaux(user)
        return user._permissions_mandat

    def has_perm(self, user, perm, obj=None) -> bool:
        return perm in self.get_all_permissions(user, obj)
