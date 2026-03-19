# utils/register_engine.py

import pandas as pd
import numpy as np
import logging
from db.database_connector import get_db_connection

logger = logging.getLogger(__name__)


def clusterizar(df):

    df['marcacionReal'] = np.nan

    return df


def process_excel_import(file_path):
    """
    Función principal del motor de registro.
    Lee el Excel con encabezados, previene 'NaN', evita duplicados exactos 
    y retorna estadísticas para el frontend.
    """
    
    # 1. ESTABLECER CONEXIÓN Y TRANSACCIÓN
    conn = get_db_connection(target_db='sistema_gestion_registros_db')
    
    if not conn:
        logger.error("No se pudo conectar a la base de datos de registros.")
        return {"exito": False, "error": "No se pudo conectar a la base de datos de registros."}

    cursor = conn.cursor(dictionary=True)
    
    try:
        # 2. CARGA DE DATOS (Pandas)
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('_', '')
        df = df.astype(object).where(pd.notna(df), None)

        # Extraemos las fechas únicas que vienen en este Excel para optimizar la BD
        df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d')
        fechas_excel = df['fecha'].dropna().unique().tolist()

        # 3. CARGAR CACHÉS (El escudo de validación y anti-duplicados)
        dept_cache = _load_departamentos_cache(cursor)
        bandera_cache = _load_banderas_cache(cursor)
        func_by_cedula, func_by_name = _load_funcionarios_cache(cursor)
        
        # Le pasamos la lista de fechas al caché de registros
        registros_cache = _load_registros_cache(cursor, fechas_excel)

        # Variables para tracking (para el log final y la vista web)
        registros_insertados = 0
        registros_omitidos = 0

        # 4. ITERACIÓN PRINCIPAL
        for index, row in df.iterrows():
            
            raw_dept = row.get('departamento')
            raw_nombre = row.get('nombre')
            raw_cedula = row.get('cedula')
            raw_marcacion = row.get('tipomarcacion')
            raw_verif = row.get('verificacion')
            
            dept_name = str(raw_dept).strip().upper() if raw_dept is not None else "GENERAL"
            excel_fullname = str(raw_nombre).strip().upper() if raw_nombre is not None else "DESCONOCIDO"

            excel_cedula = str(raw_cedula).replace('.0', '').strip() if raw_cedula is not None else None
            if excel_cedula and excel_cedula.lower() in ['nan', 'none', '<na>', '']:
                excel_cedula = None

            # --- A. Gestión de Departamento ---
            if dept_name not in dept_cache:
                dept_id = _create_departamento(cursor, dept_name)
                dept_cache[dept_name] = dept_id
            else:
                dept_id = dept_cache[dept_name]

            # --- B. Gestión de Funcionario ---
            funcionario_id = None
            if excel_cedula and excel_cedula in func_by_cedula:
                funcionario_id = func_by_cedula[excel_cedula]
            elif excel_fullname in func_by_name:
                funcionario_id = func_by_name[excel_fullname]

            # --- C. Creación de Funcionario ---
            if not funcionario_id:
                nombres, apellidos = _split_fullname(excel_fullname)
                funcionario_id = _create_funcionario(cursor, dept_id, nombres, apellidos, excel_cedula)
                if excel_cedula: 
                    func_by_cedula[excel_cedula] = funcionario_id
                func_by_name[excel_fullname] = funcionario_id

            # --- D. Limpieza y formateo de Fecha, Hora y Marcación ---
            marcacion_clean = str(raw_marcacion).strip().upper() if raw_marcacion is not None else ""
            if marcacion_clean not in bandera_cache:
                raise ValueError(f"Fila {index + 2}: La bandera '{marcacion_clean}' no existe en la BD.")
            bandera_id = bandera_cache[marcacion_clean]
            
            raw_fecha = row.get('fecha')
            if not raw_fecha or str(raw_fecha).lower() == 'nan':
                raise ValueError(f"Fila {index + 2}: La fecha está vacía o es inválida.")
            fecha_str = str(raw_fecha)
                
            raw_hora = row.get('hora')
            hora_str = str(raw_hora).strip() if raw_hora is not None else '00:00:00'
            # Asegurar que la hora tenga formato HH:MM:SS para comparar bien
            if len(hora_str.split(':')) == 2:
                hora_str += ":00"
            # Rellena con 0 a la izquierda si la hora es de un solo dígito (ej: 8:00:00 -> 08:00:00)
            hora_str = hora_str.zfill(8)

            # E. FILTRO ANTI-DUPLICADOS
            # Creamos una llave única: "IDFuncionario_Fecha_Hora"
            registro_key = f"{funcionario_id}_{fecha_str}_{hora_str}"
            
            if registro_key in registros_cache:
                # Si ya existe en la base de datos o en una fila anterior, lo ignoramos
                registros_omitidos += 1
                continue
            
            # Si no existe, preparamos el método y lo insertamos
            verif_str = str(raw_verif).strip().upper() if raw_verif is not None else ""
            if 'FACE' in verif_str: metodo = 'FACE'
            elif 'FING' in verif_str or 'FP' in verif_str: metodo = 'FP'
            elif 'OMR' in verif_str: metodo = 'OMR'
            else: metodo = 'MANUAL'
            
            _create_registro_actividad(cursor, funcionario_id, fecha_str, hora_str, bandera_id, metodo)
            
            # Lo agregamos al caché en memoria para bloquear filas clonadas en el mismo Excel
            registros_cache.add(registro_key)
            registros_insertados += 1

        # 5. COMMIT
        conn.commit()
        logger.info(f"Importación completada. Insertados: {registros_insertados} | Omitidos por duplicidad: {registros_omitidos}")
        
        # Retornamos el diccionario para que el controlador web muestre los mensajes exactos
        return {
            "exito": True,
            "insertados": registros_insertados,
            "omitidos": registros_omitidos
        }

    except Exception as e:
        # 6. ROLLBACK
        conn.rollback()
        logger.error(f"Error crítico durante la importación. Rollback ejecutado. Detalles: {e}")
        return {"exito": False, "error": str(e)}
    
    finally:
        # 7. CERRAR RECURSOS
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# FUNCIONES AUXILIARES (Consultas directas a la BD sistema_gestion_registros_db)

def _load_registros_cache(cursor, fechas_excel):
    if not fechas_excel:
        return set()
        
    format_strings = ','.join(['%s'] * len(fechas_excel))
    
    # Extraemos directamente las columnas sin usar funciones de formato de MySQL
    query = f"""
        SELECT id_funcionario, fecha_registro, hora_registro 
        FROM registros_actividad
        WHERE fecha_registro IN ({format_strings})
    """
    
    cursor.execute(query, tuple(fechas_excel))
    
    cache = set()
    for r in cursor.fetchall():
        fecha_str = r['fecha_registro'].strftime('%Y-%m-%d') if hasattr(r['fecha_registro'], 'strftime') else str(r['fecha_registro'])
        
        hora_str = str(r['hora_registro']).split('.')[0] 
        if len(hora_str.split(':')) == 2:
            hora_str += ":00"
            
        hora_str = hora_str.zfill(8)
            
        cache.add(f"{r['id_funcionario']}_{fecha_str}_{hora_str}")
        
    return cache

def _load_departamentos_cache(cursor):
    cursor.execute("SELECT id_departamento, nombre_departamento FROM departamentos")
    return {r['nombre_departamento'].upper(): r['id_departamento'] for r in cursor.fetchall()}

def _load_banderas_cache(cursor):
    cursor.execute("SELECT id_bandera, nombre_bandera FROM banderas_actividad")
    return {r['nombre_bandera'].upper(): r['id_bandera'] for r in cursor.fetchall()}

def _load_funcionarios_cache(cursor):
    cursor.execute("SELECT id_funcionario, nombres, apellidos, cedula FROM funcionarios")
    rows = cursor.fetchall()
    by_cedula = {r['cedula']: r['id_funcionario'] for r in rows if r['cedula']}
    by_name = {f"{r['apellidos']} {r['nombres']}".upper(): r['id_funcionario'] for r in rows}
    return by_cedula, by_name

def _create_departamento(cursor, name):
    sql = "INSERT INTO departamentos (nombre_departamento) VALUES (%s)"
    cursor.execute(sql, (name,))
    return cursor.lastrowid

def _split_fullname(fullname):
    parts = fullname.split()
    if len(parts) >= 4:
        apellidos = f"{parts[0]} {parts[1]}"
        nombres = " ".join(parts[2:])
    elif len(parts) == 3:
        apellidos = f"{parts[0]} {parts[1]}"
        nombres = parts[2]
    else:
        apellidos = parts[0] if len(parts) > 0 else "N/A"
        nombres = " ".join(parts[1:]) if len(parts) > 1 else "N/A"
    return nombres, apellidos

def _create_funcionario(cursor, dept_id, nombres, apellidos, cedula):
    sql = """
        INSERT INTO funcionarios (id_departamento, nombres, apellidos, cedula) 
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (dept_id, nombres, apellidos, cedula))
    return cursor.lastrowid

def _create_registro_actividad(cursor, func_id, fecha, hora, bandera_id, metodo):
    sql = """
        INSERT INTO registros_actividad (id_funcionario, fecha_registro, hora_registro, id_bandera, metodo_registro) 
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (func_id, fecha, hora, bandera_id, metodo))