import json
from vsm_app.utils.sap_rfc import call_sap_rfc
from vsm_app.models import VSM, VSMProducto

vsm = VSM.objects.get(id=99)

cabecera = {
    "legajo": str(vsm.retirante.legajo).zfill(8),
    "fecha": vsm.fecha_entrega.strftime("%d.%m.%Y"),
    "id_doc": str(vsm.id).zfill(3),
    "cod_mov": "201",
}

items = []
for vp in VSMProducto.objects.filter(vsm=vsm):
    items.append({
        "cod_mat": str(vp.producto.codigo),
        "centro": "1001",
        "almacen": "G001",
        "cantidad": f"{float(vp.cantidad_entregada):.3f}",
        "kostl": vsm.centro_costos.codigo if vsm.centro_costos else "",
    })

params = {"I_CAB": cabecera, "IT_ITEMS": items}

print("📤 Enviando RFC ZRFC_INOUT_SMARTSAFETY con:")
print(json.dumps(params, indent=2))

resultado = call_sap_rfc("ZRFC_INOUT_SMARTSAFETY", params, debug=True)

print(resultado)

print("\n📥 Resultado recibido:")
print(json.dumps(resultado, indent=2))

if resultado and "E_MATDOC" in resultado:
    print("\n✅ Código de documento SAP:", resultado["E_MATDOC"])
else:
    print("\n⚠️ No se recibió E_MATDOC en la respuesta")
