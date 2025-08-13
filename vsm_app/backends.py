from pprint import pprint
from django.contrib.auth.models import User
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.sessions.models import Session
import time
from django.conf import settings

class CustomOIDCBackend(OIDCAuthenticationBackend):

    def get_token(self, payload):
        return super().get_token(payload)    

    def get(self, request):
        time.sleep(1) 
        super().get(request)
    
    def create_user(self, claims):
        email = claims.get('email')
        given_name = claims.get('given_name', '')
        group_attributes = claims.get('group_attributes', [])

        user = User.objects.create_user(username=email, email=email, first_name=given_name)
        user.given_name = given_name

        if group_attributes:
            user.group_name = group_attributes[0]

            if 'Admin' in group_attributes:
                user.is_superuser = True
                user.is_staff = True
            
            elif 'rinde_only' in group_attributes:
                user.is_staff = True

        user.save()
        return user

    def update_user(self, user, claims):
        email = claims.get('email')
        given_name = claims.get('given_name', None)
        group_attributes = claims.get('group_attributes', [])

        user.username = email
        user.email = email
        user.first_name = given_name
        user.given_name = given_name

        if group_attributes:
            user.group_name = group_attributes[0]

            if 'Admin' in group_attributes:
                user.is_superuser = True
                user.is_staff = True

            elif 'rinde_only' in group_attributes:
                user.is_staff = True
            
            else:
                user.is_superuser = False
                user.is_staff = False
        else:
            user.is_superuser = False
            user.is_staff = False

        user.save()
        return user