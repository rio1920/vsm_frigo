import os
import django
import pandas as pd

# ✅ 1. Configurar settings ANTES de cualquier import de modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vsm_frigo.settings')

# ✅ 2. Inicializar Django
django.setup()

# ✅ 3. Ahora sí, importar modelos
from vsm_app.models import centro_costos, maestro_de_materiales, PermisoRetiro

# ✅ 4. Lógica de carga
df = pd.read_excel("materiales_expandido2.xlsx")

for _, row in df.iterrows():
    codigo_prod = str(row['Codigo de producto']).strip()
    codigo_cc = str(row['CentroCosto']).strip()

    try:
        prod = maestro_de_materiales.objects.get(codigo=codigo_prod)
    except maestro_de_materiales.DoesNotExist:
        print(f"⚠ Producto {codigo_prod} no encontrado")
        continue

    try:
        cc = centro_costos.objects.get(codigo=codigo_cc)
    except centro_costos.DoesNotExist:
        print(f"⚠ Centro de costo {codigo_cc} no encontrado")
        continue

    permiso, _ = PermisoRetiro.objects.get_or_create(centro_costo=cc)
    permiso.producto.add(prod)

print("✅ Permisos cargados correctamente")
