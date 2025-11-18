import os
import re
import html
import json
import requests
import xml.etree.ElementTree as ET
from test_saponoso import Saponoso
from vsm_app.models import VSMProducto

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

    try:
        response = requests.post(base_url, auth=auth, headers=headers, data=payload, verify=False, timeout=30)

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
                text = (item.text or "").strip()
                if not text:
                    continue

                try:
                    text = html.unescape(text)

                    record = json.loads(text)
                    result[tag_name].append(record)
                except json.JSONDecodeError:
                    record = {child.tag: child.text for child in item}
                    result[tag_name].append(record)
    return result

def get_stock_sap_multiple(codigos: list[str], centro: str = "1000", almacen: str = "1100", debug: bool = False) -> dict[str, int]:
    codigos_norm = [c.lstrip("0") for c in codigos]
    stock_dict = {c: 0 for c in codigos} 

    params = {
        "I_WERKS": centro,
        "I_LGORT": almacen,
        "T_MATNR": codigos,
    }

    data = call_sap_rfc("ZRFC_STOCK_SMARTSAFETY", params)

    if not data:
        print("⚠️ Sin respuesta de SAP o error en el RFC.")
        return stock_dict

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

def enviar_entrega_sap(vsm, debug=False):
    """
    Envía los datos de una entrega (VSM) a SAP mediante el RFC ZRFC_INOUT_SMARTSAFETY
    y devuelve el número de documento de material si la operación fue exitosa.
    """
    import json
    from vsm_app import models
    from vsm_app.utils.sap_rfc import call_sap_rfc

    try:
        # 🧾 Cabecera
        cabecera = {
            "legajo": str(vsm.retirante.legajo if vsm.retirante else ""),
            "fecha": vsm.fecha_entrega.strftime("%d.%m.%Y"),
            "id_doc": str(vsm.id).zfill(18),
            "cod_mov": "201",
        }

        # 📦 Items
        items = []
        for vp in models.VSMProducto.objects.filter(vsm=vsm):
            cantidad = float(vp.cantidad_entregada or 0)
            if cantidad <= 0:
                continue 

            items.append({
                "cod_mat": str(vp.producto.codigo).zfill(18),
                "centro": "1001",   
                "almacen": "G001",
                "cantidad": cantidad,
                "kostl": vsm.centro_costos.codigo if vsm.centro_costos else "",
            })

        if not items:
            return {"success": False, "error": "⚠️ No hay ítems con cantidad para enviar a SAP."}

        params = {"I_CAB": cabecera, "IT_ITEMS": items}

        resultado = call_sap_rfc("ZRFC_INOUT_SMARTSAFETY", params)
        if not resultado:
            return {"success": False, "error": "💥 No se recibió respuesta del servidor SAP (resultado = None)."}

        e_return = resultado.get("E_RETURN", {})

        mensaje = (
            e_return.get("MESSAGE")
            or e_return.get("message")
            or "Sin mensaje devuelto por SAP"
        )

        mat_doc = e_return.get("MAT_DOC") or e_return.get("mat_doc")
        doc_year = e_return.get("DOC_YEAR") or e_return.get("doc_year")

        if mat_doc and doc_year:
            return {
                "success": True,
                "mat_doc": mat_doc,
                "doc_year": doc_year,
            }

        if "LEGAJO" in mensaje.upper() or "ERROR" in mensaje.upper():
            return {"success": False, "error": f"💥 SAP devolvió un error: {mensaje}"}

        return {"success": False, "error": f"⚠️ SAP devolvió: {mensaje}"}

    except Exception as e:
        return {"success": False, "error": f"💥 Excepción Python: {str(e)}"}

def enviar_entrega_a_sap(vsm):
    """
    Envía una entrega VSM al SAP vía SOAP RFC ZRFC_INOUT_SMARTSAFETY.
    Imprime en consola el JSON exacto que se envía y la respuesta.
    """
    sap = Saponoso(
        endpoint="qas",  # Cambiar a "pro" en producción
        username=os.environ.get("SAP_USERNAME", "COMM_USER1"),
        password=os.environ.get("SAP_PASSWORD", "Sistemas2013"),
        verify_ssl=False,
        debug=True,          # 🔍 activa salida detallada
        pretty_xml=False     # podés poner True si querés ver el XML completo
    )

    cabecera = {
        "LEGAJO": str(vsm.retirante.legajo),
        "FECHA": vsm.fecha_entrega.strftime("%Y%m%d"),
        "ID_DOC": str(vsm.id),
        "COD_MOV": "201"
    }

    items = []
    for vp in VSMProducto.objects.filter(vsm=vsm):
        items.append({
            "COD_MAT": str(vp.producto.codigo),
            "CENTRO": "1001",
            "ALMACEN": "G001",
            "CANTIDAD": f"{vp.cantidad_entregada:.3f}",
            "KOSTL": str(vsm.centro_costos.codigo).zfill(10)
        })

    params = {
        "I_CAB": cabecera,
        "IT_ITEMS": items
    }

    print("\n📤 Enviando a SAP ZRFC_INOUT_SMARTSAFETY con parámetros:")
    print(json.dumps(params, indent=2, ensure_ascii=False))

    try:
        resultado = sap.call_rfc("ZRFC_INOUT_SMARTSAFETY", params)

        print("\n📥 Respuesta recibida de SAP:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

        e_return = resultado.get("E_RETURN", {})
        mat_doc = e_return.get("MAT_DOC", {}).get("value")
        doc_year = e_return.get("DOC_YEAR", {}).get("value")
        mensaje = e_return.get("MESSAGE", {}).get("value")

        if mat_doc:
            print(f"✅ Entrega enviada correctamente. Documento: {mat_doc} / Año: {doc_year}")
            return {"success": True, "mat_doc": mat_doc, "doc_year": doc_year, "mensaje": mensaje}

        print("⚠️ SAP devolvió mensaje sin documento:")
        print(json.dumps(e_return, indent=2, ensure_ascii=False))
        return {"success": False, "error": f"SAP devolvió error: {mensaje or 'Sin mensaje'}"}

    except Exception as e:
        print(f"💥 Error al enviar a SAP: {e}")
        return {"success": False, "error": f"Error al enviar a SAP: {e}"}
