# test_env.py
from decouple import config

print("OIDC_RP_CLIENT_ID =", config("OIDC_RP_CLIENT_ID_"))
