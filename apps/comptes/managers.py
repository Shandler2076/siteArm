from django.contrib.auth.base_user import BaseUserManager


class CompteManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, identifiant, password=None, **extra):
        from apps.comptes.models import normaliser_identifiant

        if not identifiant or not identifiant.strip():
            raise ValueError("L'identifiant est obligatoire.")
        compte = self.model(identifiant=normaliser_identifiant(identifiant), **extra)
        compte.set_password(password)
        compte.save(using=self._db)
        return compte

    def create_superuser(self, identifiant, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("doit_changer_mot_de_passe", False)
        return self.create_user(identifiant, password, **extra)
