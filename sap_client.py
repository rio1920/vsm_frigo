import httpx
import re
from datetime import date
from django.conf import settings


def call_rfc_tropa_cab(fecha_desde: str, fecha_hasta: str):
    """
    Llama al RFC ZZ_RFC_WH_TROPA_CAB en SAP vía SOAP.
    Retorna los datos parseados o lanza una excepción en caso de error.
    """

    base_url = settings.SAP_BASE_URL
    auth = (settings.SAP_USERNAME, settings.SAP_PASSWORD)

    headers = {"Content-Type": "text/xml; charset=utf-8"}

    payload = f"""<?xml version="1.0"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:urn="urn:sap-com:document:sap:rfc:functions">
        <soapenv:Body>
            <urn:ZRFC_STOCK_SMARTSAFETY>
            </urn:ZRFC_STOCK_SMARTSAFETY>
        </soapenv:Body>
        </soapenv:Envelope>"""

    with httpx.Client(verify=False, timeout=60.0) as client:
        response = client.post(base_url, auth=auth, headers=headers, content=payload)

        if response.status_code != 200:
            raise Exception(f"Error SAP: {response.status_code} - {response.text}")

        print(response.text)


def extract_data_from_soap(xml_text: str):
    """
    Extrae los valores de <E_RETURN><item>...</item></E_RETURN> del XML SOAP.
    Retorna una lista de listas, separando por '|'.
    """
    matches = re.findall(r"<E_RETURN><item>(.*?)</item></E_RETURN>", xml_text)
    if not matches:
        return []

    return [row.split("|") for row in matches]
