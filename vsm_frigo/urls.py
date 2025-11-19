from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from mozilla_django_oidc.views import OIDCLogoutView
from vsm_app.logout import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
    path(
        "auth/login/",
        RedirectView.as_view(url="/oidc/authenticate/", permanent=True),
        name="keycloak_login",
    ),
    path("auth/logout/", LogoutView.as_view(), name="keycloak_logout"),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path('', include('vsm_app.urls')),
]

