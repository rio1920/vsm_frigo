
from pathlib import Path
import os
import sys
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-&&gvd#+73!rkj4#x(ffqb@4%lk946jv42ky)&e-y0)5cys$!%+'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'vsm_app',  
    'mozilla_django_oidc',
    'corsheaders',
    'django_browser_reload',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "mozilla_django_oidc.middleware.SessionRefresh",
    "corsheaders.middleware.CorsMiddleware",
]

AUTHENTICATION_BACKENDS = [
    'vsm_app.backends.CustomOIDCBackend',
    'django.contrib.auth.backends.ModelBackend',
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'vsm_frigo.urls'
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "vsm_app/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "vsm_app.context_processors.user_context",
            ],
        },
    },
]

WSGI_APPLICATION = 'vsm_frigo.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "vsm_frigo_local",
        "USER": "postgres",
        "PASSWORD": "Pilar+2023",
        "HOST": "localhost",
        "PORT": "5432",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


KEYCLOAK_EXEMPT_URIS = []
KEYCLOAK_CONFIG = {
    "KEYCLOAK_SERVER_URL": "http://localhost:8000/auth",
    "KEYCLOAK_REALM": "pandora",
    "KEYCLOAK_CLIENT_ID": "vsm_frigo",
    "KEYCLOAK_CLIENT_SECRET_KEY": "gRsKix6tJ62rUDddRFyCe798Dc6jMcFD",
    "KEYCLOAK_CACHE_TTL": 60,
    "LOCAL_DECODE": False,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "django_keycloak_auth",
        "TIMEOUT": KEYCLOAK_CONFIG["KEYCLOAK_CACHE_TTL"],
        "KEY_PREFIX": "django_keycloak_auth_",
    }
}
CACHE_MIDDLEWARE_KEY_PREFIX = "django_keycloak_auth_"

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


OIDC_RP_CLIENT_ID = config("OIDC_RP_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = config("OIDC_RP_CLIENT_SECRET")
OIDC_RP_SIGN_ALGO = config("OIDC_RP_SIGN_ALGO")

OIDC_OP_JWKS_ENDPOINT = config("OIDC_OP_JWKS_ENDPOINT")
OIDC_OP_AUTHORIZATION_ENDPOINT = config("OIDC_OP_AUTHORIZATION_ENDPOINT")
OIDC_OP_TOKEN_ENDPOINT = config("OIDC_OP_TOKEN_ENDPOINT")
OIDC_OP_USER_ENDPOINT = config("OIDC_OP_USER_ENDPOINT")

LOGIN_REDIRECT_URL = config("LOGIN_REDIRECT_URL")
LOGOUT_REDIRECT_URL = config("LOGOUT_REDIRECT_URL")
LOGIN_URL = config("LOGIN_URL")

OIDC_REDIRECT_ALLOWED_HOSTS = "vsm.rioplatense.local", "127.0.0.1:8000"

USE_X_FORWARDED_HOST = True

OIDC_REDIRECT_REQUIRE_HTTPS = True


OIDC_VERIFY_SSL = False




# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/


STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, "vsm_app/static")]


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
