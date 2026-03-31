""" [EXPERIMENTAL] CONTROLADOR EXPERIMENTAL PARA ESCALABILIDAD """

from flask import render_template, session, current_app, flash
from fpdf import FPDF
from datetime import date
from db.database_connector import get_db_connection
from utils.file_manager import get_omr_storage
import os
import json
import qrcode
import tempfile
import logging
logging.basicConfig(level=logging.INFO)


# 1. FUNCIÓN QUE GENERA EL PDF Y EL QR

def generar_formato_omr_limpio(nombre_archivo, empleado_nombre, empleado_id, fecha, departamento, ruta_logo=None, qr_data_dict=None):
    # Generar el QR dinámico en un archivo temporal si hay datos
    ruta_qr_temp = None
    if qr_data_dict:
        # Configuracion de el QR
        qr_obj = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=1)
        qr_obj.add_data(json.dumps(qr_data_dict))
        qr_obj.make(fit=True)
        img_qr = qr_obj.make_image(fill_color="black", back_color="white")

        temp_qr_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img_qr.save(temp_qr_file.name)
        ruta_qr_temp = temp_qr_file.name

    # 1. Configuración inicial
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    
    # =========================================================================
    # NUEVO: DIBUJAR MARCAS DE REGISTRO (FIDUCIALES)
    # Cuadrados negros sólidos de 6x6 mm con un margen seguro de 8 mm
    # =========================================================================
    margen_x = 8
    margen_y = 8
    l_marca = 6 # Tamaño del cuadrado
    
    pdf.set_fill_color(0, 0, 0) # Relleno negro puro
    
    # Esquina Arriba-Izquierda
    pdf.rect(margen_x, margen_y, l_marca, l_marca, style='F')
    # Esquina Arriba-Derecha
    pdf.rect(210 - margen_x - l_marca, margen_y, l_marca, l_marca, style='F')
    # Esquina Abajo-Izquierda
    pdf.rect(margen_x, 294 - margen_y - l_marca, l_marca, l_marca, style='F')
    # Esquina Abajo-Derecha
    pdf.rect(210 - margen_x - l_marca, 294 - margen_y - l_marca, l_marca, l_marca, style='F')
    # =========================================================================
    
    # Encabezado: Logo
    if ruta_logo and os.path.exists(ruta_logo):
        # Ajustamos un poco la Y del logo para alinearlo con las marcas
        pdf.image(ruta_logo, x=18, y=16, w=15, h=15)
    else:
        pdf.set_font("helvetica", style="I", size=8)
        pdf.text(18, 24, "LOGO")
    
    # Cuadro y Código QR (Ajustado para no solapar la marca derecha)
    pdf.rect(160, 15, 35, 35)
    if ruta_qr_temp:
        # Colocamos la imagen del QR dentro del cuadro ajustado
        pdf.image(ruta_qr_temp, x=160.5, y=15.5, w=34, h=34)
        os.remove(ruta_qr_temp) # Limpiamos el archivo temporal automáticamente
    else:
        pdf.set_font("helvetica", style="I", size=10) 
        pdf.text(168, 35, "[ QR AQUÍ ]")
    
    # Título Principal (Ajustado en Y)
    pdf.set_font("helvetica", style="B", size=14)
    pdf.set_xy(30, 15) 
    pdf.cell(130, 6, "HOJA DE REGISTRO DIARIO DE ASISTENCIA", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=9)
    pdf.set_x(30)
    pdf.cell(130, 4, "(Formato para OMR)", align="C", new_x="LMARGIN", new_y="NEXT")
    
    # Datos del Empleado (Ajustado inicio en Y a 36)
    pdf.set_xy(10, 36)
    pdf.set_font("helvetica", style="B", size=11)
    
    pdf.cell(18, 6, "Nombre:", border=0)
    pdf.set_font("helvetica", size=11)
    pdf.cell(80, 6, empleado_nombre, border=0)
    
    pdf.set_font("helvetica", style="B", size=11)
    pdf.cell(15, 6, "Fecha:", border=0)
    pdf.set_font("helvetica", size=11)
    pdf.cell(35, 6, fecha, border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", style="B", size=11)
    pdf.cell(18, 6, "Área:", border=0)
    pdf.set_font("helvetica", size=11)
    pdf.cell(80, 6, departamento, border=0)
    
    pdf.set_font("helvetica", style="B", size=11)
    pdf.cell(15, 6, "ID:", border=0)
    pdf.set_font("helvetica", size=11)
    pdf.cell(35, 6, empleado_id, border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    # Línea divisoria ajustada a los márgenes
    pdf.line(14, pdf.get_y(), 194, pdf.get_y())
    pdf.ln(1)

    # Función interna para dibujar bloques
    def dibujar_bloque_marcacion(pdf, titulo, pos_y):
        pdf.set_xy(10, pos_y)
        pdf.set_font("helvetica", style="B", size=12)
        pdf.cell(190, 6, titulo, border=0, new_x="LMARGIN", new_y="NEXT")
        
        caja_y = pos_y + 7
        pdf.set_line_width(0.5)
        pdf.rect(10, caja_y, 190, 24) 
        pdf.line(10, caja_y + 12, 200, caja_y + 12)
        
        radio = 2.5
        diametro = radio * 2
        inicio_x = 34
        separacion = 14
        offset_text = 1.9
        
        pdf.set_line_width(0.6) 
        
        # FILA DE HORAS (7 a 18)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.text(14.5, caja_y + 8, "HORA:")
        
        horas = list(range(7, 19))
        for i, h in enumerate(horas):
            centro_x = inicio_x + (i * separacion)
            centro_y = caja_y + 4.3
            pdf.set_font("helvetica", style="B", size=10)
            pdf.text(centro_x - offset_text, centro_y -1, f"{h:02d}")
            pdf.ellipse(centro_x - radio, centro_y, diametro, diametro)

        # FILA DE MINUTOS (00 a 55)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.text(12, caja_y + 20, "MINUTOS:")
        
        minutos = list(range(0, 60, 5))
        for i, m in enumerate(minutos):
            centro_x = inicio_x + (i * separacion)
            centro_y = caja_y + 16.3
            pdf.set_font("helvetica", style="B", size=10)
            pdf.text(centro_x - offset_text, centro_y - 1, f"{m:02d}")
            pdf.ellipse(centro_x - radio, centro_y, diametro, diametro)
            
        pdf.set_line_width(0.5)
        return caja_y + 25

    # Dibujar secciones
    y_actual = pdf.get_y()
    y_actual = dibujar_bloque_marcacion(pdf, "1. ENTRADA PRINCIPAL", y_actual)
    y_actual = dibujar_bloque_marcacion(pdf, "2. SALIDA INTERMEDIA (Descanso)", y_actual)
    y_actual = dibujar_bloque_marcacion(pdf, "3. ENTRADA INTERMEDIA (Retorno)", y_actual)
    y_actual = dibujar_bloque_marcacion(pdf, "4. SALIDA PRINCIPAL", y_actual)
    y_actual = dibujar_bloque_marcacion(pdf, "ENTRADA JUSTIFICADA", y_actual)
    y_actual = dibujar_bloque_marcacion(pdf, "SALIDA JUSTIFICADA", y_actual)

    # NUEVA SECCIÓN: Motivos y Área de Firma
    pos_y = y_actual
    pdf.set_xy(10, pos_y)
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(80, 6, "MOTIVO DE JUSTIFICACIÓN", border=0, new_x="LMARGIN", new_y="NEXT")
    
    caja_y = pos_y + 7
    pdf.set_line_width(0.5)
    pdf.rect(10, caja_y, 80, 18) 
    
    radio = 2.5
    diametro = radio * 2
    pdf.set_line_width(0.6)
    pdf.set_font("helvetica", style="B", size=10)
    
    opciones = [
        ("MÉDICO", 18, caja_y + 3.5),     ("PERSONAL", 56, caja_y + 3.5),
        ("COMISIÓN", 18, caja_y + 10.5),  ("OTRO", 56, caja_y + 10.5)
    ]
    
    for texto, x_pos, y_pos in opciones:
        pdf.ellipse(x_pos, y_pos, diametro, diametro)
        pdf.text(x_pos + 7, y_pos + 4, texto) 
        
    firma_y = caja_y + 13 
    pdf.set_line_width(0.5)
    pdf.line(100, firma_y, 195, firma_y) 
    
    pdf.set_xy(125, firma_y + 1)
    pdf.set_font("helvetica", style="B", size=11)
    pdf.cell(46, 8, "FIRMA DEL EMPLEADO", align="C", border=0)

    pdf.set_y(caja_y + 22) 
    pdf.set_font("helvetica", size=11)
    pdf.multi_cell(0, 4, "Certifico que las marcas en este documento son válidas para ser auditadas por personal calificado.", align="C")

    pdf.output(nombre_archivo)
    return os.path.abspath(nombre_archivo)


# 2. CONTROLADOR FLASK main.py
def generate_format_omr():
    usuario_id = session.get('user_id')
    
    # Valores por defecto en caso de error
    empleado_nombre = "Usuario Desconocido"
    departamento = "No Asignado"
    
    # Consultar datos del usuario en la Base de Datos
    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            sql = """
                SELECT CONCAT(u.apellidos, ' ', u.nombres) AS nombre_completo, d.departamento 
                FROM usuarios u
                INNER JOIN departamentos d ON u.id_departamento = d.id_departamento
                WHERE u.id_usuario = %s
            """
            cursor.execute(sql, (usuario_id,))
            resultado = cursor.fetchone()
            if resultado:
                empleado_nombre = resultado[0]
                departamento = resultado[1]
    except Exception as e:
        flash("Error al consultar usuario para generar el documento.", "error")
        logging.error(f"Error al consultar usuario para OMR: {e}")
    finally:
        if conexion:
            conexion.close()

    # Formatear el ID como EMP-00000 (incremento automático basado en su ID de BD)
    codigo_emp = f"EMP-{usuario_id:05d}"
    
    # Obtener fecha actual
    fecha_hoy = date.today().strftime('%d/%m/%Y')

    # Datos para el JSON del QR
    datos_qr = {
        "id": codigo_emp,
        "nombre": empleado_nombre,
        "fecha": fecha_hoy,
        "departamento": departamento,
        "tipo_archivo": "OMR_ASISTENCIA_DIARIA"
    }

    # Definir ruta de guardado usando el file_manager
    storage_path = get_omr_storage()
    nombre_pdf = f"GENERATE-{codigo_emp}-OMR.pdf"
    ruta_completa_pdf = os.path.join(storage_path, nombre_pdf)

    # Generar el PDF dinámico (sobreescribe si es el mismo usuario otro día)
    ruta_del_logo = os.path.join(current_app.root_path, 'static', 'img', 'logo-reloj-bk.png')

    generar_formato_omr_limpio(
        nombre_archivo=ruta_completa_pdf,
        empleado_nombre=empleado_nombre,
        empleado_id=codigo_emp,
        fecha=fecha_hoy,
        departamento=departamento,
        ruta_logo=ruta_del_logo,
        qr_data_dict=datos_qr
    )

    flash("¡Documento generado y listo para imprimir!", "success")
    flash("Recuerda seguir las instrucciones de uso.")

    # Retornamos la plantilla enviándole el nombre del archivo para renderizarlo
    return render_template('users/preview_omr.html', pdf_filename=nombre_pdf)