import os
import uuid
import pandas as pd

from flask import render_template, request, jsonify, session
from utils.file_manager import get_temp_uploads_storage, get_uploads_storage_parquet
from utils.register_engine import clusterizar

def upload_xlsx_page_controller():
    """Renderiza la vista HTML para subir el Excel"""
    return render_template('users/upload_xlsx_view.html')

def process_upload_xlsx_controller():
    """
    Paso 1: Sube el archivo, lo guarda como temporal, lee con Pandas
    para validar que tenga las columnas correctas y cuenta las filas para el resumen.
    """
    # verifica que el archivo de la petición HTTP llegue desde al frontend
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró ningún archivo en la petición"}), 400

    file = request.files['file']

    # validar que el file realmente exista
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    # verifica la extensión y archivo
    if file and file.filename.lower().endswith('.xlsx'):
        try:
            # Validar perfil administrativo
            rol_actual = session.get('rol_id')
            if rol_actual != 1:
                return jsonify({"error": "Acceso denegado. Solo el perfil administrativo puede cargar registros."}), 403

            # Guardar temporalmente el archivo
            temp_folder = get_temp_uploads_storage()
            extension = os.path.splitext(file.filename)[1]
            temp_filename = f"temp_xlsx_{uuid.uuid4().hex}{extension}"
            temp_filepath = os.path.join(temp_folder, temp_filename)
            file.save(temp_filepath)

            # Validación rápida con Pandas
            df = pd.read_excel(temp_filepath)

            # Renombre de columnas para la validación
            df = df.rename(columns={
                'Dpto.': 'departamento',
                'Nombre': 'nombre'
            })

            total_filas = len(df)

            # Conteo de personal único (forzando a string para evitar errores con números/códigos)
            total_personal = df['nombre'].astype(str).nunique() if 'nombre' in df.columns else 0

            # función Number of Unique (nunique()) para conteo (len()) dentro de pandas, solo si existe la col departamento
            total_dept = df['departamento'].nunique() if 'departamento' in df.columns else 0

            # Retornamos el nombre del archivo temporal al frontend
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
            return jsonify({"error": f"Error interno al procesar el Excel: {str(e)}"}), 500
    else:
        return jsonify({"error": "Formato inválido. Solo se admiten archivos .xlsx."}), 400

def cancel_upload_xlsx_controller():
    """Descarta el archivo temporal si el usuario cancela la operación."""
    datos = request.get_json()
    filename = datos.get('filename')
    if filename:
        temp_folder = get_temp_uploads_storage()
        filepath = os.path.join(temp_folder, filename)
        if "temp_xlsx_" in filename and os.path.exists(filepath):
            os.remove(filepath)
    return jsonify({"mensaje": "Archivo descartado correctamente."}), 200

def confirm_upload_xlsx_controller():
    """
    Paso 2: Toma el archivo temporal, aplica las transformaciones finales,
    lo convierte a .parquet y elimina el temporal.
    """
    datos_req = request.get_json()
    if not datos_req or 'archivo_temp' not in datos_req:
        return jsonify({"error": "Datos inválidos o falta el archivo temporal, error interno."}), 400

    archivo_temp = datos_req.get('archivo_temp')
    temp_folder = get_temp_uploads_storage()
    temp_filepath = os.path.join(temp_folder, archivo_temp)

    if not os.path.exists(temp_filepath):
        return jsonify({"error": "El archivo temporal ya no existe o caducó. Vuelva a subirlo."}), 400

    try:
        # 1. leer el archivo temporal nuevamente
        df = pd.read_excel(temp_filepath)

        # 2. filtrado
        df = df.rename(columns={
            'Dpto.': 'departamento',
            'Nombre': 'nombre',
            'AC_No': 'numAcceso',
            'Fecha/Hora': 'fecha_hora',
            'Marc-Ent/Sal': 'tipoMarcacion',
            'Reloj ID': 'relojID',
            'No. Cédula': 'cedula',
            'Incidencia': 'incidencia',
            'Verificación': 'verificacion',
            'CardNo': 'numTarjeta'
        })

        if 'verificacion' in df.columns:
            df['verificacion'] = df['verificacion'].str.upper()

        df = df.drop(columns=['relojID', 'incidencia', 'numTarjeta'], errors='ignore')

        # Conversión de fechas
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], format='%d/%m/%Y %H:%M:%S')
        df['fecha'] = df['fecha_hora'].dt.date
        df['hora'] = df['fecha_hora'].dt.time

        # 3. cluster y validaciones
        total_personal = total_personal = df['nombre'].astype(str).nunique() if 'nombre' in df.columns else 0

        df = clusterizar(df)  # función para cluster

        total_marcaciones = df['tipoMarcacion'].astype(str).nunique() if 'tipoMarcacion' in df.columns else 0

        # 4. Generar nombre y guardar el .parquet
        year = str(df['fecha_hora'].dt.year.unique()[0])
        mes = str(df['fecha_hora'].dt.month.unique()[0]).zfill(2)  # zfill para agregar 0 en casos como 09-
        archivo_parquet = f"{mes}-{year}.parquet"

        folder = get_uploads_storage_parquet()
        filepath = os.path.join(folder, archivo_parquet)

        df.to_parquet(filepath, engine='pyarrow', compression='snappy')

        # 5. Eliminar el archivo temporal (.xlsx)
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        # 6. Responder al frontend
        if total_personal > 0:
            total_registros_guardados = len(df)
            return jsonify({
                "mensaje": f"Se guardaron {total_registros_guardados} registros correspondientes a {total_marcaciones} tipos de marcaciones.",
                "tipo": "success"
            }), 200
        else:
            return jsonify({"error": "Error: Los datos no fueron cargados correctamente."}), 500

    except Exception as e:
        return jsonify({"error": f"Error crítico en la confirmación: {str(e)}"}), 500