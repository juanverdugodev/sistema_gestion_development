""" [EXPERIMENTAL] CONTROLADOR EXPERIMENTAL PARA ESCALABILIDAD """

import os
import uuid
import shutil
from flask import render_template, request, jsonify, session
from utils.file_manager import get_temp_uploads_storage, get_final_omr_storage
from utils.omr_engine import OMREngine
from db.database_connector import get_db_connection
from datetime import datetime

def upload_page_controller():
    return render_template('users/upload_omr_view.html') 

def process_upload_controller():
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró ningún archivo en la petición"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        try:
            # 1. Validar que el usuario en sesión es ADMINISTRADOR (id_rol = 1)
            rol_actual = session.get('rol_id')
            if rol_actual != 1:
                return jsonify({"error": "Acceso denegado. Solo el perfil administrativo puede procesar marcaciones."}), 403
            
            # 2. Guardar temporalmente el archivo (usamos un nombre genérico, ya no atado al admin)
            temp_folder = get_temp_uploads_storage()
            extension = os.path.splitext(file.filename)[1]
            temp_filename = f"temp_omr_{uuid.uuid4().hex}{extension}"
            temp_filepath = os.path.join(temp_folder, temp_filename)
            file.save(temp_filepath)

            # 3. INSTANCIAR EL ESCÁNER OMR Y PROCESAR
            motor_omr = OMREngine()
            resultado = motor_omr.procesar_documento(temp_filepath)

            # 4. Evaluar resultado del OMR
            if resultado["estado"] == "ERROR":
                os.remove(temp_filepath)
                return jsonify({"error": resultado["mensaje"]}), 400
            
            # 5. Éxito
            return jsonify({
                "mensaje": resultado["mensaje"],
                "archivo_temp": temp_filename,
                "estado": "pendiente_validacion",
                "datos": resultado["datos"] 
            }), 200

        except Exception as e:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            return jsonify({"error": f"Error interno al procesar: {str(e)}"}), 500
    else:
        return jsonify({"error": "Formato inválido. Solo se admiten archivos PDF."}), 400
    

def cancel_upload_controller():
    datos = request.get_json()
    filename = datos.get('filename')
    if filename:
        temp_folder = get_temp_uploads_storage()
        filepath = os.path.join(temp_folder, filename)
        if "temp_" in filename and os.path.exists(filepath):
            os.remove(filepath)
    return jsonify({"mensaje": "Archivo descartado correctamente."}), 200


def confirm_upload_controller():
    datos_req = request.get_json()
    if not datos_req or 'datos' not in datos_req:
        return jsonify({"error": "Datos inválidos"}), 400

    scanned_data = datos_req['datos']
    archivo_temp = datos_req.get('archivo_temp')
    fecha_str_original = scanned_data.get('fecha_documento')
    
    # MODIFICACIÓN CLAVE: Extraemos el ID del empleado que fue leído del QR
    # Asumimos que el motor OMR ya descompuso "EMP-00003" y guardó un "3" en id_usuario
    usuario_id = scanned_data.get('id_usuario')
    
    if not usuario_id:
        return jsonify({"error": "El documento no contiene un código QR de empleado válido."}), 400

    # Conversión de Fecha
    try:
        fecha_obj = datetime.strptime(fecha_str_original, '%d/%m/%Y')
        fecha_str = fecha_obj.strftime('%Y-%m-%d')
    except ValueError:
        try:
            fecha_obj = datetime.strptime(fecha_str_original, '%Y-%m-%d')
            fecha_str = fecha_str_original
        except ValueError:
            return jsonify({"error": f"Formato de fecha inválido: {fecha_str_original}"}), 400

    motivo_just = scanned_data.get('motivo_justificacion')
    detalle_just = scanned_data.get('detalle_justificacion')

    db = get_db_connection()
    try:
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT id_usuario FROM usuarios WHERE id_usuario = %s", (usuario_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"El empleado escaneado (ID: {usuario_id}) no existe en el sistema."}), 404

        # 1. Obtener o crear el registro del Mes
        mes_nombre = fecha_obj.strftime('%B').capitalize()
        anio = fecha_obj.year
        
        cursor.execute("SELECT id_meses FROM registros_meses_sistema WHERE meses_sistema = %s AND anio = %s", (mes_nombre, anio))
        mes_record = cursor.fetchone()
        
        if not mes_record:
            cursor.execute("INSERT INTO registros_meses_sistema (meses_sistema, anio) VALUES (%s, %s)", (mes_nombre, anio))
            id_mes = cursor.lastrowid
        else:
            id_mes = mes_record['id_meses']

        # 2. Insertar o recuperar el registro_dia (Asignado al usuario_id del QR)
        cursor.execute("SELECT id_dias FROM registro_dias WHERE id_usuario = %s AND fecha_registro = %s", (usuario_id, fecha_str))
        dia_record = cursor.fetchone()
        
        if dia_record:
            id_dia = dia_record['id_dias']
            cursor.execute("""
                UPDATE registro_dias 
                SET motivo_justificacion = %s, detalle_justificacion = %s 
                WHERE id_dias = %s
            """, (motivo_just, detalle_just, id_dia))
            cursor.execute("DELETE FROM registro_horas WHERE id_dias = %s AND origen = 'omr'", (id_dia,))
        else:
            cursor.execute("""
                INSERT INTO registro_dias (id_meses, id_usuario, fecha_registro, motivo_justificacion, detalle_justificacion)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_mes, usuario_id, fecha_str, motivo_just, detalle_just))
            id_dia = cursor.lastrowid

        # 3. Obtener el ID del estado "Pendiente"
        cursor.execute("SELECT id_estado FROM estados_revision WHERE tipo = 'Pendiente'")
        estado_record = cursor.fetchone()
        id_estado_pendiente = estado_record['id_estado'] if estado_record else 1

        # 4. Mapeo del JSON
        mapa_secciones = {
            'entrada_principal': 'Entrada principal', 
            'salida_intermedia': 'Salida intermedia (Descanso)', 
            'entrada_intermedia': 'Entrada intermedia (Retorno)', 
            'salida_principal': 'Salida principal', 
            'entrada_justificada': 'Entrada justificada', 
            'salida_justificada': 'Salida justificada'
        }

        # 5. Insertar las horas
        for key_json, hora_valor in scanned_data.get('entradas_salidas', {}).items():
            if hora_valor: 
                nombre_tipo = mapa_secciones.get(key_json)
                cursor.execute("SELECT id_tipo FROM tipos_marcacion WHERE codigo = %s", (nombre_tipo,))
                tipo_record = cursor.fetchone()
                
                if tipo_record:
                    cursor.execute("""
                        INSERT INTO registro_horas (id_dias, id_tipo_marcacion, id_estado_revision, origen, hora)
                        VALUES (%s, %s, %s, 'omr', %s)
                    """, (id_dia, tipo_record['id_tipo'], id_estado_pendiente, hora_valor))

        # 6. MOVER Y RENOMBRAR EL ARCHIVO FÍSICO
        if archivo_temp:
            ruta_temp = os.path.join(get_temp_uploads_storage(), archivo_temp)
            if os.path.exists(ruta_temp):
                carpeta_destino = get_final_omr_storage(usuario_id) 
                codigo_emp = f"EMP-{int(usuario_id):05d}"
                nuevo_nombre = f"{codigo_emp}-{fecha_str}.pdf" 
                
                ruta_final = os.path.join(carpeta_destino, nuevo_nombre)
                shutil.move(ruta_temp, ruta_final)

        db.commit()        
        return jsonify({"mensaje": f"Datos guardados correctamente para el empleado {codigo_emp}."}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Error de base de datos: {str(e)}"}), 500
    finally:
        if db:
            db.close()