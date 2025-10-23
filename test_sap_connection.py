import requests
import re

# Desactiva warnings SSL de SAP (por certificados internos)
requests.packages.urllib3.disable_warnings()

def extract_data_from_soap(xml_text):
    matches = re.findall(r"<E_RETURN><item>(.*?)</item></E_RETURN>", xml_text)
    if not matches:
        print("⚠️ No se encontró ningún <E_RETURN> en la respuesta SOAP.")
        return None
    return [row.split("|") for row in matches]

def main():
    base_url = "https://frclouds4qas.rioplatense.local:10443/sap/bc/soap/rfc"
    auth = ("comm_user1", "Sistemas2013")
    headers = {"Content-Type": "text/xml; charset=utf-8"}

    payload = """<?xml version="1.0"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:urn="urn:sap-com:document:sap:rfc:functions">
        <soapenv:Body>
            <urn:ZRFC_STOCK_SMARTSAFETY>
            </urn:ZRFC_STOCK_SMARTSAFETY>
        </soapenv:Body>
        </soapenv:Envelope>"""

    try:
        print("🔗 Conectando a SAP...")
        response = requests.post(base_url, auth=auth, headers=headers, data=payload, verify=False, timeout=30)
        print(f"✅ HTTP Status: {response.status_code}")

        if response.status_code == 200:
            print("📦 Respuesta SOAP recibida:")
            print(response.text[:800])  # Mostramos solo el inicio
            data = extract_data_from_soap(response.text)
            if data:
                print("✅ Datos extraídos correctamente:")
                for row in data:
                    print(row)
            else:
                print("❌ No se pudo extraer información útil del XML.")
        else:
            print(f"❌ Error en la respuesta: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"💥 Error de conexión: {e}")

if __name__ == "__main__":
    main()
