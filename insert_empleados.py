import psycopg2
import pyodbc
from environs import Env
import polars as pl
import logging
import datetime

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("actualizacion_db.log"),
        logging.StreamHandler()
    ]
)

env = Env()
env.read_env()

# Conexión SQL Server
try:
    con_db_origen = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={env('DB_HOST_ORIGEN')};"
        f"DATABASE={env('DB_NAME_ORIGEN')};"
        f"UID={env('DB_USER_ORIGEN')};"
        f"PWD={env('DB_PASSWORD_ORIGEN')};"
        f"PORT={env('DB_PORT_ORIGEN')};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    logging.info("Conexión a SQL Server establecida correctamente.")
except Exception as e:
    logging.error("Error al conectar con la base de datos origen (SQL Server).", exc_info=True)
    raise

# Conexión PostgreSQL
try:
    con_db_destino = psycopg2.connect(
        host=env("DB_HOST_DESTINO"),
        user=env("DB_USER_DESTINO"),
        password=env("DB_PASSWORD_DESTINO"),
        database=env("DB_NAME_DESTINO"),
        port=env("DB_PORT_DESTINO")
    )
    logging.info("Conexión a PostgreSQL establecida correctamente.")
except Exception as e:
    logging.error("Error al conectar con la base de datos destino (PostgreSQL).", exc_info=True)
    con_db_origen.close()
    raise

# Query SQL para traer los datos
query = """
        SELECT DISTINCT
            Personal.LegNume AS Legajo,
            Personal.LegApNo AS Nombre_Apellido,
            Plantas.PlaDesc AS Empresa,
            Personal.LegSect AS CC,
            Personal.LegTipo AS Tipo_liq,
            Personal.LegFeIN AS Fecha_Ingreso,
            Personal.LegFeEg AS Fecha_Egreso,
            RIGHT('0000000000' + CAST(Identifica.IDTarjeta AS VARCHAR), 10) AS NROTARJETA
        FROM
            dbo.PERSONAL Personal
        INNER JOIN
            dbo.IDENTIFICA Identifica ON Personal.LegNume = Identifica.IDLegajo
        LEFT OUTER JOIN
            sectores ON Personal.LegSect = sectores.seccodi
        LEFT OUTER JOIN
            dbo.PLANTAS Plantas ON Personal.LegPlan = Plantas.PlaCodi
        WHERE
            Personal.LegNume > 0 AND
            (Personal.LegPlan < 751 OR Personal.LegPlan IN (900, 904, 905, 910, 916, 919))
        ORDER BY
            Personal.LegNume
"""
 
try:
    df = pl.read_database(query=query, connection=con_db_origen)
    logging.info(f"Consulta SQL ejecutada correctamente. Total filas: {len(df)}")
except Exception as e:
    logging.error("Error al ejecutar la consulta SQL.", exc_info=True)
    con_db_origen.close()
    con_db_destino.close()
    raise

# Limpieza de fecha inválida

df = df.with_columns([
    pl.when(pl.col("Fecha_Egreso") == datetime.datetime(1753, 1, 1))
      .then(None)
      .otherwise(pl.col("Fecha_Egreso"))
      .alias("Fecha_Egreso")
])

# Agregamos la columna "active" por defecto en False

df = df.with_columns([
    pl.lit(False).alias("active")
])

# Datos para tabla empleado

columnas_empleado = ["legajo", "nombre", "cc", "active"]
df_empleados = df.select(columnas_empleado)

# Datos para tabla tarjeta (se llenará luego de actualizar el campo active)

df_tarjetas = (
    df.filter((pl.col("nro_tarjeta").is_not_null()))
      .select(["Legajo", "nro_tarjeta"])
      .unique()
)

# Query de inserción/actualización de empleados

query_upsert_empleado = """
    INSERT INTO public."vsm_app_empleados"(legajo, nombre, cc_id, active)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (legajo) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        cc_id = EXCLUDED.cc_id,
        legajo = EXCLUDED.legajo,
        active = EXCLUDED.active
"""

# Query de inserción de tarjetas (evitando duplicados)

query_insert_tarjeta = """
    INSERT INTO public."vsm_app_nro_tarjeta"(nrotarjeta, empleado_id)
    VALUES (%s, %s)
    ON CONFLICT (nrotarjeta) DO UPDATE SET
        empleado_id = EXCLUDED.empleado_id
"""

try:
    with con_db_destino.cursor() as cursor:
        # Paso 1: Insertar/actualizar empleados con active=False
        logging.info(f"Iniciando inserción/actualización de {len(df_empleados)} empleados con active=False.")
        for row in df_empleados.iter_rows(named=True):
            try:
                cursor.execute(query_upsert_empleado, (
                    row["legajo"],
                    row["nombre"],
                    row["cc_id"],
                    row["tipo_liq"],
                    False  # Fuerza el valor False siempre
                ))
            except Exception as e:
                con_db_destino.rollback()
                logging.error(f"Error en empleado Legajo={row['legajo']}: {e}")

        # Paso 2: Actualizar el campo 'active' de los empleados con fechas válidas
        hoy = datetime.datetime.today()
        df_estado = (
            df.group_by("legajo")
              .agg([
                  pl.col("Fecha_Egreso").max().alias("ultima_baja")
              ])
              .filter((pl.col("ultima_baja").is_null()) | (pl.col("ultima_baja") > hoy))
        )
        logging.info(f"Actualizando {len(df_estado)} empleados como activos.")
        for row in df_estado.iter_rows(named=True):
            try:
                cursor.execute(
                    'UPDATE public."vsm_app_empleados" SET active = TRUE WHERE legajo = %s',
                    (row["legajo"],)
                )
            except Exception as e:
                con_db_destino.rollback()
                logging.error(f"Error actualizando activo Legajo={row['legajo']}: {e}")
 
        # Paso 3: Insertar/actualizar tarjetas solo para empleados activos
        logging.info(f"Iniciando inserción de tarjetas ({len(df_tarjetas)} registros).")
        for row in df_tarjetas.iter_rows(named=True):
            try:
                cursor.execute(
                    'SELECT active FROM public."vsm_app_empleados" WHERE legajo = %s',
                    (row["legajo"],)
                )
                result = cursor.fetchone()
                if result and result[0]:  # Solo insertar si active es True
                    cursor.execute(query_insert_tarjeta, (
                        row["nro_tarjeta"],
                        row["legajo"]
                    ))
            except Exception as e:
                con_db_destino.rollback()
                logging.error(f"Error en tarjeta Legajo={row['legajo']}, NRO={row['nro_tarjeta']}: {e}")


        # Paso 4: Eliminar tarjetas obsoletas
        cursor.execute('SELECT nro_tarjeta FROM public."vsm_app_nro_tarjeta"')
        tarjetas_db = {row[0] for row in cursor.fetchall()}
        tarjetas_actuales = set(df_tarjetas["nro_tarjeta"].to_list())
        tarjetas_obsoletas = tarjetas_db - tarjetas_actuales
 
        logging.info(f"Eliminando {len(tarjetas_obsoletas)} tarjetas obsoletas.")
        for nro in tarjetas_obsoletas:
            try:
                cursor.execute(
                    'DELETE FROM public."vsm_app_nro_tarjetas" WHERE nro_tarjeta = %s', (nro,)
                )
            except Exception as e:
                con_db_destino.rollback()
                logging.error(f"Error al eliminar tarjeta obsoleta {nro}: {e}")

except Exception as e:
    logging.error(f"Error general durante el proceso: {e}")
    con_db_destino.rollback()

finally:
    con_db_origen.close()
    con_db_destino.close()
    logging.info("Conexiones cerradas.")