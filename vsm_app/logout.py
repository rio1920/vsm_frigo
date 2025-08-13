from mozilla_django_oidc.views import OIDCLogoutView
from django.conf import settings

def keycloak_logout(request):
    logout_endpoint = settings.OIDC_OP_LOGOUT_ENDPOINT
    return logout_endpoint + "?redirect_uri=" + \
           request.build_absolute_uri(settings.LOGOUT_REDIRECT_URL)

class LogoutView(OIDCLogoutView):
    def get(self, request):
        return self.post(request)