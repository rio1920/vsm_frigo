import os
import re
import html
import json
import requests
import xml.etree.ElementTree as ET

# Evitar warnings SSL
requests.packages.urllib3.disable_warnings()


def call_sap_rfc(rfc_name: str, params: dict | None = None, debug: bool = False) -> dict | None:
    """
    Llama a un RFC SOAP en SAP y devuelve las tablas internas en un dict.
    Si debug=True, imprime el XML enviado y la respuesta completa.
    """
    SAP_ENV = os.getenv("SAP_ENV", "QAS").upper()

    BASE_URLS = {
        "QAS": "https://frclouds4qas.rioplatense.local:10443/sap/bc/soap/rfc",
        "PRO": "https://frclouds4pro.rioplatense.local:10443/sap/bc/soap/rfc",
    }

    base_url = BASE_URLS.get(SAP_ENV)
    if not base_url:
        raise ValueError(f"Entorno SAP desconocido: {SAP_ENV}")

    auth = (
        os.getenv("SAP_USER", "comm_user1"),
        os.getenv("SAP_PASS", "Sistemas2013"),
    )

    # Construcción del body XML
    body_params = ""
    if params:
        for k, v in params.items():
            if isinstance(v, list):  # listas de materiales
                body_params += f"<{k}>"
                for item in v:
                    body_params += f"<item><MATNR>{item}</MATNR></item>"
                body_params += f"</{k}>"
            else:
                body_params += f"<{k}>{v}</{k}>"

    payload = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:urn="urn:sap-com:document:sap:rfc:functions">
        <soapenv:Body>
            <urn:{rfc_name}>
                {body_params}
            </urn:{rfc_name}>
        </soapenv:Body>
    </soapenv:Envelope>"""

    headers = {"Content-Type": "text/xml; charset=utf-8"}

    if debug:
        print("\n================ XML ENVIADO ================\n")
        print(payload)
        print("============================================\n")

    try:
        response = requests.post(base_url, auth=auth, headers=headers, data=payload, verify=False, timeout=30)

        if debug:
            print("\n================ RESPUESTA SAP ================\n")
            print(response.text[:1000])  # Limitar a primeros 1000 caracteres
            print("==============================================\n")

        if response.status_code != 200:
            print(f"❌ Error HTTP {response.status_code}: {response.text[:400]}")
            return None

        return parse_soap_response(response.text)

    except requests.exceptions.RequestException as e:
        print(f"💥 Error de conexión con SAP ({SAP_ENV}): {e}")
        return None


def parse_soap_response(xml_text: str) -> dict:
    """
    Convierte la respuesta SOAP en un dict.
    Si SAP devuelve JSON embebido en los <item>, también lo decodifica.
    """
    ns = {"soap": "http://schemas.xmlsoap.org/soap/envelope/",
          "urn": "urn:sap-com:document:sap:rfc:functions"}

    root = ET.fromstring(xml_text)
    body = root.find("soap:Body", ns)
    if body is None:
        return {"error": "Sin <soap:Body> en la respuesta"}

    result = {}

    for table in body.iter():
        tag_name = re.sub(r"^{.*}", "", table.tag)
        if len(table):
            if tag_name not in result:
                result[tag_name] = []

            for item in table.findall("item"):
                # Tomar el texto (que podría ser JSON escapado)
                text = (item.text or "").strip()
                if not text:
                    continue

                try:
                    # Desescapar entidades HTML (&#34; -> ")
                    text = html.unescape(text)

                    # Intentar parsear como JSON
                    record = json.loads(text)
                    result[tag_name].append(record)
                except json.JSONDecodeError:
                    # Si no es JSON, procesar como XML normal
                    record = {child.tag: child.text for child in item}
                    result[tag_name].append(record)

    return result


def get_stock_sap_multiple(codigos: list[str], centro: str = "1000", almacen: str = "1100", debug: bool = False) -> dict[str, int]:
    codigos_norm = [c.lstrip("0") for c in codigos]  # quitar ceros a la izquierda
    stock_dict = {c: 0 for c in codigos}  # mantener la clave original

    params = {
        "I_WERKS": centro,
        "I_LGORT": almacen,
        "T_MATNR": codigos,
    }

    data = call_sap_rfc("ZRFC_STOCK_SMARTSAFETY", params)

    if not data:
        print("⚠️ Sin respuesta de SAP o error en el RFC.")
        return stock_dict

    if debug:
        print("📦 Datos crudos recibidos de SAP:")
        for item in data.get("E_RETURN", []):
            print(item.get("MATNR"), item.get("LABST"))

    tabla_stock = data.get("T_STOCK") or data.get("STOCK") or data.get("E_RETURN") or []
    for item in tabla_stock:
        matnr_sap = item.get("MATNR", "").strip().lstrip("0")
        labst = int(float(item.get("LABST", "0")))

        if matnr_sap in codigos_norm:
            index = codigos_norm.index(matnr_sap)
            stock_dict[codigos[index]] = labst

    return stock_dict




def get_stock_sap(codigo: str, centro: str = "1000", almacen: str = "1100", debug: bool = False) -> int:
    """
    Consulta el stock de un solo material.
    """
    stocks = get_stock_sap_multiple([codigo], centro, almacen, debug=debug)
    return stocks.get(codigo, 0)
