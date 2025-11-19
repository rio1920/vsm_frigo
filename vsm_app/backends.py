from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from .models import Usuarios

 
 
class CustomOIDCBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        email = claims.get("email")
        given_name = claims.get("given_name", "")
        family_name = claims.get("family_name", "")

        user = Usuarios.objects.create_user(
            username=email,
            email=email,
            first_name=given_name,
            last_name=family_name,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        user.save()
        return user
    

    def update_user(self, user, claims):
        email = claims.get("email")
        given_name = claims.get("given_name", "")
        family_name = claims.get("family_name", "")
 
        user.email = email
        user.first_name = given_name
        user.last_name = family_name

        user.save()
        return user