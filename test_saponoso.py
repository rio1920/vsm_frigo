"""_summary_
    Clase para facilitar la llamada de RFC via SOAP a SAP y parsear las respuestas en diccionarios de Python.
   
 
    Raises:
        ValueError: Si la respuesta no contiene un cuerpo SOAP válido.
 
    Returns:
        _type_: _description_
"""
 
import json
import os
from typing import Any, Dict
 
import httpx
from lxml import etree
 
 
class Saponoso:
    """
    SAP on OSO (Orchestrated SOAP Operations)
    Encapsulates SAP SOAP RFC calling and parses responses into Python dictionaries.
    """
    endpoints = {
        "pro": os.environ.get("SAP_ENDPOINT_PRO", "https://frclouds4pro.rioplatense.local:10443/sap/bc/soap/rfc"),
        "qas": os.environ.get("SAP_ENDPOINT_QAS", "https://frclouds4qas.rioplatense.local:10443/sap/bc/soap/rfc"),
    }
 
    def __init__(self, **kwargs):
        endpoint = Saponoso.endpoints.get(kwargs.get("endpoint", "qas"))
        username = kwargs.get("username") or os.environ.get("SAP_USERNAME")
        password = kwargs.get("password") or os.environ.get("SAP_PASSWORD")
        if not endpoint:
            raise ValueError("SAP endpoint is not set. Please provide --endpoint or set SAP_ENDPOINT_PRO/SAP_ENDPOINT_QAS environment variables.")
        if not username:
            raise ValueError("SAP username is not set. Please provide --username or set SAP_USERNAME environment variable.")
        if not password:
            raise ValueError("SAP password is not set. Please provide --password or set SAP_PASSWORD environment variable.")
        self.endpoint = str(endpoint)
        self.username = str(username)
        self.password = str(password)
        self.introspect = kwargs.get("introspect", False)
        self.pretty_xml = kwargs.get("pretty_xml", False)
        self.debug = kwargs.get("debug", False)
        self.verify_ssl = kwargs.get("verify_ssl", False)
        self.timeout = kwargs.get("timeout", 10.0)
 
    def call_rfc(self, rfc_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call the SAP RFC via SOAP and parse the response."""
        soap_envelope = self._build_soap_envelope(rfc_name, params)
        if self.debug:
            print(f"Calling RFC '{rfc_name}' with params: {params}")
            print(f"SOAP Envelope:\n{soap_envelope}")
           
        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            response = client.post(
                self.endpoint,
                content=soap_envelope.encode('utf-8'),
                headers=headers,
                auth=(self.username, self.password)
            )
        response.raise_for_status()
        if self.debug:
            print(f"RFC call executed successfully.\n{response.text}")
        return self.parse_response(response.text)
 
    def _build_soap_envelope(self, rfc_name: str, params: Dict[str, Any]) -> str:
        """Builds a SOAP envelope for the RFC call."""
        param_xml = ''.join(f'<{k}>{v}</{k}>' for k, v in params.items())
 
        return f"""<?xml version="1.0"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:urn="urn:sap-com:document:sap:rfc:functions">
            <soapenv:Body>
 
                {self.dict_to_soap_body_element(rfc_name, params)}
 
            </soapenv:Body>
        </soapenv:Envelope>
        """
 
    def dict_to_soap_body_element(self, tag, data, namespace=None):
        """
        Recursively converts a dictionary into an XML element suitable for SOAP body insertion.
       
        Args:
            tag (str): The root tag name for the SOAP operation (e.g., 'RFC_READ_TABLE').
            data (dict): The input dictionary to convert.
            namespace (str): Optional namespace URI to apply to all tags.
       
        Returns:
            lxml.etree.Element: The root XML element.
        """
        ns = f"{{{namespace}}}" if namespace else ""
 
        def build_element(parent, key, value):
            if isinstance(value, dict):
                elem = etree.SubElement(parent, f"{ns}{key}")
                for k, v in value.items():
                    build_element(elem, k, v)
            elif isinstance(value, list):
                list_container = etree.SubElement(parent, f"{ns}{key}")
                for item in value:
                    item_elem = etree.SubElement(list_container, "item")
                    if isinstance(item, dict):
                        for k, v in item.items():
                            build_element(item_elem, k, v)
                    else:
                        item_elem.text = str(item)
            else:
                elem = etree.SubElement(parent, f"{ns}{key}")
                elem.text = str(value)
 
        NS_RFC = "urn:sap-com:document:sap:rfc:functions"
        nsmap = {"urn": NS_RFC}
 
        root = etree.Element(f"{{urn:sap-com:document:sap:rfc:functions}}{tag}", nsmap=nsmap)
 
        for k, v in data.items():
            build_element(root, k, v)
 
        return etree.tostring(root, pretty_print=True, encoding="unicode")
 
 
    def parse_response(self, xml_text: str):
        """Parse all response variables from SOAP XML and decode payloads. Handles tables as lists of dicts."""
        tree = etree.fromstring(xml_text.encode('utf-8'))
        if self.pretty_xml:
            print("--- Raw XML Response --------------------------------")
            print(xml_text.replace('><','>\n<'))
            print("-^^ Raw XML Response ^^------------------------------")
        body = tree.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body')
        if body is None:
            raise ValueError("No <SOAP-ENV:Body> found in response.")
 
        # Find the RFC response element (first child of Body)
        rfc_response = next(body.iterchildren(), None)
        if rfc_response is None:
            raise ValueError("No RFC response element found in SOAP Body.")
        results = {}
        for var_elem in rfc_response.iterchildren():
            var_name = etree.QName(var_elem).localname
            # If the variable has children and all are <item>, treat as table
            if len(var_elem) and all(etree.QName(child).localname == "item" for child in var_elem.iterchildren()):
                table = []
                for item in var_elem.iterchildren():
                    row = {}
                    for col in item.iterchildren():
                        col_key = etree.QName(col).localname
                        col_val = col.text.strip() if col.text and col.text.strip() else None
                        row[col_key] = self._decode_payload(col_val) if col_val is not None else None
                    table.append(row)
                results[var_name] = {
                    'type': 'table',
                    'value': table
                }
            elif len(var_elem):
                # Structure or nested elements
                sub_results = {}
                for sub_elem in var_elem.iterchildren():
                    sub_key = etree.QName(sub_elem).localname
                    if sub_elem.text is None or not sub_elem.text.strip():
                        sub_parsed_val = None
                        sub_type = 'NoneType'
                    else:
                        sub_text_val = sub_elem.text.strip()
                        sub_parsed_val = self._decode_payload(sub_text_val)
                        sub_type = type(sub_parsed_val).__name__
                    sub_results[sub_key] = {
                        'type': sub_type,
                        'value': sub_parsed_val
                    }
                results[var_name] = sub_results
            else:
                if var_elem.text is None or not var_elem.text.strip():
                    parsed_val = None
                    val_type = 'NoneType'
                else:
                    text_val = var_elem.text.strip()
                    parsed_val = self._decode_payload(text_val)
                    val_type = type(parsed_val).__name__
                results[var_name] = {
                    'type': val_type,
                    'value': parsed_val
                }
        if self.introspect:
            print("--- Introspection ---")
            for k, v in results.items():
                print(f"Variable: {k}")
                if isinstance(v, dict) and 'type' in v and 'value' in v:
                    print(f"  Type: {v['type']}")
                    print(f"  Value: {repr(v['value'])}\n")
                elif isinstance(v, list):
                    print(f"  Table with {len(v)} rows")
                    for i, row in enumerate(v):
                        print(f"    Row {i}: {row}")
                else:
                    for sub_k, sub_v in v.items():
                        print(f"  Sub-variable: {sub_k}")
                        print(f"    Type: {sub_v['type']}")
                        print(f"    Value: {repr(sub_v['value'])}\n")
        return results
 
    def _decode_payload(self, val: str) -> Any:
        try:
            parsed = json.loads(val)
            return parsed
        except Exception:
            pass
        if val.isdigit():
            return int(val)
        try:
            float_val = float(val)
            return float_val
        except Exception:
            pass
        return val
 
# Example usage:
# client = SAPRFCClient(endpoint="http://sap-server:8000/sap/bc/soap_rfc", username="user", password="pass")
# result = client.call_rfc("ZRFC_name", {"input_variable_name": "param_value"})
# print(result)
 
if __name__ == "__main__":
    import argparse
    from pprint import pprint
    parser = argparse.ArgumentParser(description="SAP RFC Response Debugger")
    parser.add_argument('--endpoint', default="qas", help="SAP endpoint (or set SAP_ENDPOINT_PRO/SAP_ENDPOINT_QAS env vars)")
    parser.add_argument('--username', help="Username (or set SAP_USERNAME env var)")
    parser.add_argument('--password', help="Password (or set SAP_PASSWORD env var)")
    parser.add_argument('--rfc', default="STFC_CONNECTION", help="RFC name")
    parser.add_argument('--params', default="{}", help="RFC parameters as JSON string")
    parser.add_argument('-f', '--file', type=str, help="JSON file containing RFC parameters")
    parser.add_argument('--introspect', action='store_true', help="Show introspection of response variables")
    parser.add_argument('--pretty-xml', action='store_true', help="Show response as pretty-printed XML")
    parser.add_argument('--debug', action='store_true', help="Enable debug output")
    args = parser.parse_args()
 
    sap = Saponoso( endpoint=args.endpoint,
                    username=args.username,
                    password=args.password,
                    introspect=args.introspect,
                    pretty_xml=args.pretty_xml,
                    timeout=getattr(args, 'timeout', 10.0),
                    debug=args.debug,
                    verify_ssl=False)
    params = {}
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                params = json.load(f)
        except Exception as e:
            print(f"Error loading params from file: {e}\nFile: {args.file}")
            params = {}
    else:
        try:
            params = json.loads(args.params)
        except Exception as e:
            print(f"Error parsing params JSON: {e}\nSupplied: {args.params}")
            params = {}
    result = sap.call_rfc(args.rfc, params)
    print("--- Parsed Result --- (to be returned to program) --------")
    pprint(result)
    print("-^^ Parsed Result ^^--------------------------------------")