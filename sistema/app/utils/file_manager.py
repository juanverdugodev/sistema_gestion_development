import os
import logging

# Instanciamos exclusivamente el canal de sistema para operaciones de I/O (Carpetas/Archivos)
sys_logger = logging.getLogger('sistema')

# Ruta base en el volumen vol-app
STORAGE_BASE_PATH = '/storage_datos/storage-files'

# FUNCIÓN para los PDFs omr
def get_omr_storage():
    pdf_path = os.path.join(STORAGE_BASE_PATH, 'pdf-emp-downloads')
    if not os.path.exists(pdf_path): 
        try:
            os.makedirs(pdf_path) 
            sys_logger.info(f"Carpeta PDF creada exitosamente en: {pdf_path}")
        except Exception as e:
            sys_logger.error(f"Error al crear la carpeta PDF: {e}")
    return pdf_path



# FUNCIÓN para los archivos temporales (Subidos para validación de usuario)
def get_temp_uploads_storage():
    temp_path = os.path.join(STORAGE_BASE_PATH, 'temp-uploads')
    if not os.path.exists(temp_path):
        try:
            os.makedirs(temp_path)
            sys_logger.info(f"Carpeta Temporal creada exitosamente en: {temp_path}")
        except Exception as e:
            sys_logger.error(f"Error al crear la carpeta Temporal: {e}")
    return temp_path


# funcion para guardar carpeta parquet
def get_uploads_storage_parquet():
    path = os.path.join(STORAGE_BASE_PATH, 'uploads', 'parquets')
    if not os.path.exists(path):
        try:
            # os.makedirs crea la carpeta 'uploads' (si no existe) y luego 'parquets' adentro
            os.makedirs(path)
            sys_logger.info(f"Carpeta de Parquets persistentes creada exitosamente en: {path}")
        except Exception as e:
            sys_logger.error(f"Error al crear la jerarquía de carpetas para Parquets: {e}")
            
    return path


# FUNCIÓN para los logs del sistema y auditoría
def get_logs_storage():
    logs_path = os.path.join(STORAGE_BASE_PATH, 'logs')
    if not os.path.exists(logs_path):
        try:
            os.makedirs(logs_path)
            # Nota: Si el logger aún no ha sido configurado en app.py, este mensaje podría 
            # no salir en el archivo físico la primera vez, pero preparará el terreno para futuros reinicios.
            sys_logger.info(f"Carpeta de Logs creada exitosamente en: {logs_path}")
        except Exception as e:
            sys_logger.error(f"Error al crear la carpeta de Logs: {e}")
            
    return logs_path



# FUNCIÓN para los PDFs finales (Validados y guardados para auditoría) Crea la estructura: /storage_datos/storage-files/uploads/omr-guardados/EMP-00001
def get_final_omr_storage(usuario_id):

    # Formateamos el ID para que tenga 5 dígitos (ej. EMP-00001)

    codigo_emp = f"EMP-{int(usuario_id):05d}"

    # Construir ruta dir
    final_path = os.path.join(STORAGE_BASE_PATH, 'uploads', 'omr-guardados', codigo_emp)

    if not os.path.exists(final_path):
        try:
            # os.makedirs crea toda la jerarquía de carpetas si no existe
            os.makedirs(final_path)
            sys_logger.info(f"Carpeta de Auditoría creada exitosamente para {codigo_emp} en: {final_path}")
        except Exception as e:
            sys_logger.error(f"Error al crear la carpeta de Auditoría para {codigo_emp}: {e}")
            
    return final_path