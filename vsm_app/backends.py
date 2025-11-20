from mozilla_django_oidc.auth import OIDCAuthenticationBackend # Necesario si usas el superuser check
from django.db.models import Q
import logging 
from vsm_app.models import permisos as Permisos


logger = logging.getLogger(__name__)

# ------------------------------------

CLAIMS_PERMISSIONS_KEY = 'Permiso_VSM' 
DEFAULT_APP_LABEL = 'vsm_app' 
SPECIAL_PERMISSIONS_MAP = {
    "admin_access": ["auth.view_user", "auth.view_group"], 
}

# ------------------------------------


class CustomOIDCBackend(OIDCAuthenticationBackend):
    def _get_keycloak_permissions(self, claims):
        
        raw_codenames = claims.get(CLAIMS_PERMISSIONS_KEY, [])
        full_codenames = set(raw_codenames)
        
        for codename in full_codenames.copy(): 
            if codename in SPECIAL_PERMISSIONS_MAP:
                full_codenames.update(SPECIAL_PERMISSIONS_MAP[codename])
        
        return full_codenames


    def _sync_permissions(self, user, claims):

        desired_permission_names = self._get_keycloak_permissions(claims)
        
        # --- DIAGNÓSTICO ---
        logger.warning(f"Sincronización de permisos iniciada para el usuario: {user.username}")
        logger.warning(f"Permisos DESEADOS de Keycloak (Nombres): {len(desired_permission_names)} -> {desired_permission_names}")
        # -------------------

        if not desired_permission_names:
            user.permisos.clear()
            return

        desired_permissions = list(Permisos.objects.filter(nombre__in=desired_permission_names))
        
        # --- DIAGNÓSTICO ---
        logger.warning(f"Permisos ENCONTRADOS en la DB: {len(desired_permissions)}")
        if len(desired_permissions) != len(desired_permission_names):
             found_names = {p.nombre for p in desired_permissions}
             missing_names = desired_permission_names - found_names
             logger.error(f"¡ADVERTENCIA! Faltan permisos en la DB: {missing_names}. Asegúrese de que los nombres coincidan exactamente.")
        # -------------------

        # 3. Asignar los permisos deseados (sobrescribiendo los anteriores)
        try:
            user.permisos.set(desired_permissions) 
            logger.warning(f"Permisos asignados con éxito a user.permisos.")
        except Exception as e:
            logger.error(f"ERROR al asignar permisos customizados: {e}")
        
        return


    def create_user(self, claims):
        user = super().create_user(claims)
        user.email = claims.get('email', '')
        user.username = claims.get('preferred_username', '')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.save()
        self._sync_permissions(user, claims)
        return user

    def update_user(self, user, claims):
        user.email = claims.get('email', user.email)
        user.username = claims.get('preferred_username', user.username)
        user.first_name = claims.get('given_name', user.first_name)
        # CORRECCIÓN DE TYPO: Usar 'family_name' para last_name
        user.last_name = claims.get('family_name', user.last_name) 
        user.save()
        self._sync_permissions(user, claims)
        return user