# upload_xlsx_controller.py

import os
import uuid
import pandas as pd
import logging # <-- Agregado

from flask import render_template, request, jsonify, session
from utils.file_manager import get_temp_uploads_storage, get_uploads_storage_parquet
from utils.register_engine import clusterizar

# --- REEMPLAZO: Instanciamos los dos canales de logs ---
audit_logger = logging.getLogger('auditoria')
sys_logger = logging.getLogger('sistema')

def upload_xlsx_page_controller():
    """Renderiza la vista HTML para subir el Excel"""
    return render_template('users/audit/upload_xlsx_view.html')

def process_upload_xlsx_controller():
    """
    Paso 1: Sube el archivo, lo guarda como temporal, lee con Pandas
    para validar que tenga las columnas correctas y cuenta las filas para el resumen.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró ningún archivo en la petición"}), 400

    file = request.files['file']
    admin_actual = session.get('username', 'Usuario Desconocido') # Capturamos usuario para auditoría

    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    if file and file.filename.lower().endswith('.xlsx'):
        try:
            rol_actual = session.get('rol_id')
            if rol_actual != 1:
                # LOG DE AUDITORÍA: Intento de subida de datos por alguien sin permisos
                audit_logger.warning(f"Intento de carga de registros denegado para el usuario '{admin_actual}'. Se requiere rol administrativo.")
                return jsonify({"error": "Acceso denegado. Solo el perfil administrativo puede cargar registros."}), 403

            temp_folder = get_temp_uploads_storage()
            extension = os.path.splitext(file.filename)[1]
            temp_filename = f"temp_xlsx_{uuid.uuid4().hex}{extension}"
            temp_filepath = os.path.join(temp_folder, temp_filename)
            file.save(temp_filepath)

            # Lectura básica solo para mostrar números en la pantalla de carga
            df = pd.read_excel(temp_filepath)

            total_filas = len(df)
            
            # Se usan los nombres originales del Excel porque aún no pasa por el engine
            total_personal = df['Nombre'].astype(str).nunique() if 'Nombre' in df.columns else 0
            total_dept = df['Dpto.'].nunique() if 'Dpto.' in df.columns else 0

            # LOG DE SISTEMA: Trazabilidad de archivos temporales en el disco duro
            sys_logger.info(f"Archivo temporal '{temp_filename}' cargado exitosamente para validación inicial.")

            return jsonify({
                "mensaje": "Archivo leído y validado correctamente.",
                "archivo_temp": temp_filename,
                "estado": "pendiente_validacion",
                "resumen": {
                    "total_filas": total_filas,
                    "total_personal": int(total_personal),
                    "total_departamentos": int(total_dept)
                }
            }), 200

        except Exception as e:
            if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            # LOG DE SISTEMA: Falla técnica leyendo el Excel temporal
            sys_logger.error(f"Error interno al procesar (Paso 1) el Excel: {str(e)}")
            return jsonify({"error": f"Error interno al procesar el Excel: {str(e)}"}), 500
    else:
        return jsonify({"error": "Formato inválido. Solo se admiten archivos .xlsx."}), 400

def cancel_upload_xlsx_controller():
    """Descarta el archivo temporal si el usuario cancela la operación."""
    datos = request.get_json()
    filename = datos.get('filename')
    admin_actual = session.get('username', 'Usuario Desconocido')

    if filename:
        temp_folder = get_temp_uploads_storage()
        filepath = os.path.join(temp_folder, filename)
        if "temp_xlsx_" in filename and os.path.exists(filepath):
            os.remove(filepath)
            # LOG DE AUDITORÍA: El usuario canceló la subida antes de importar
            audit_logger.info(f"El usuario '{admin_actual}' descarto el archivo de validacion antes de realizar la importacion.")
            
    return jsonify({"mensaje": "Archivo descartado correctamente."}), 200

def confirm_upload_xlsx_controller():
    """
    Paso 2: Toma el archivo temporal, aplica las transformaciones de data science,
    lo convierte a .parquet y elimina el temporal.
    """
    datos_req = request.get_json()
    admin_actual = session.get('username', 'Usuario Desconocido')

    if not datos_req or 'archivo_temp' not in datos_req:
        return jsonify({"error": "Datos inválidos o falta el archivo temporal, error interno."}), 400

    archivo_temp = datos_req.get('archivo_temp')
    temp_folder = get_temp_uploads_storage()
    temp_filepath = os.path.join(temp_folder, archivo_temp)

    if not os.path.exists(temp_filepath):
        sys_logger.warning(f"Intento de confirmación fallido. El archivo temporal '{archivo_temp}' ya no existe.")
        return jsonify({"error": "El archivo temporal ya no existe o caducó. Vuelva a subirlo."}), 400

    try:
        # 1. Leer crudo
        df_raw = pd.read_excel(temp_filepath)

        # 2. Pasar al motor (El motor hace el renombre y los cálculos del Notebook)
        df, df_resumen, df_diario = clusterizar(df_raw)

        # 3. Datos finales post-procesamiento
        total_personal = df['nombre'].astype(str).nunique() if 'nombre' in df.columns else 0
        total_marcaciones = df['tipoMarcacion'].astype(str).nunique() if 'tipoMarcacion' in df.columns else 0

        # 4. Generar subcarpeta y guardar los 3 Parquets
        year = str(df['fecha_hora'].dt.year.dropna().unique()[0])
        mes = str(df['fecha_hora'].dt.month.dropna().unique()[0]).zfill(2)
        
        # Nombre de la nueva subcarpeta (Ej: "03-2026")
        nombre_subcarpeta = f"{mes}-{year}"
        base_folder = get_uploads_storage_parquet()
        
        # Ruta completa de la subcarpeta
        specific_folder = os.path.join(base_folder, nombre_subcarpeta)
        
        # Crear la subcarpeta si no existe (exist_ok=True evita errores si ya existe)
        os.makedirs(specific_folder, exist_ok=True)

        # Definir los nombres de los 3 archivos
        archivo_principal = f"{mes}-{year}.parquet"
        archivo_resumen = f"resumen-{mes}-{year}.parquet"
        archivo_diario = f"diario-{mes}-{year}.parquet"

        # Guardar los 3 DataFrames dentro de la subcarpeta específica
        df.to_parquet(os.path.join(specific_folder, archivo_principal), engine='pyarrow', compression='snappy')
        df_resumen.to_parquet(os.path.join(specific_folder, archivo_resumen), engine='pyarrow', compression='snappy')
        df_diario.to_parquet(os.path.join(specific_folder, archivo_diario), engine='pyarrow', compression='snappy')

        # 5. Limpieza
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        # 6. Respuesta
        if total_personal > 0:
            # LOG DE AUDITORÍA CRÍTICO: Registra la inyección oficial de datos a la base del sistema
            audit_logger.info(f"El usuario '{admin_actual}' proceso e importo exitosamente {len(df)} registros para el periodo {mes}-{year}.")
            return jsonify({
                "mensaje": f"Se procesaron {len(df)} registros correspondientes a {total_marcaciones} tipos de marcaciones.",
                "tipo": "success"
            }), 200
        else:
            sys_logger.error(f"Fallo lógico en el motor matemático: Los datos de {mes}-{year} terminaron vacíos tras clústerización.")
            return jsonify({"error": "Error: Los datos no fueron cargados correctamente tras el análisis."}), 500

    except Exception as e:
        # LOG DE SISTEMA: Fallo crítico durante K-Means, guardado de Parquets, etc.
        sys_logger.error(f"Error crítico en la confirmación o procesamiento matemático (Paso 2): {str(e)}")
        return jsonify({"error": f"Error crítico en la confirmación o procesamiento matemático: {str(e)}"}), 500