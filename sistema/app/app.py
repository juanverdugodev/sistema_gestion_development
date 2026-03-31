import os
import secrets
from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
from utils.file_manager import get_logs_storage

def setup_loggers():
    """Configura dos canales de logs: Sistema y Auditoría"""
    logs_dir = get_logs_storage()
    
    # --- Forzar creación física de carpeta y archivos ---
    os.makedirs(logs_dir, exist_ok=True)
    
    sistema_log = os.path.join(logs_dir, 'sistema.log')
    auditoria_log = os.path.join(logs_dir, 'auditoria.log')
    
    # crear en blanco los archivos si no existen en el disco
    open(sistema_log, 'a').close()
    open(auditoria_log, 'a').close()
    # -----------------------------------------------------------------------
    
    # --- FORMATOS INDEPENDIENTES ---
    # Formato Auditoría: Limpio y enfocado en la acción humana
    audit_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    # Formato Sistema: Técnico. Añadimos [%(filename)s:%(funcName)s]
    sys_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(funcName)s] - %(message)s')

    # --- 1. LOGGER DE SISTEMA (Errores, arranques, fallos de código) ---
    sys_handler = RotatingFileHandler(sistema_log, maxBytes=5*1024*1024, backupCount=3)
    sys_handler.setFormatter(sys_formatter) # <-- Aplicamos el formato técnico
    
    sys_logger = logging.getLogger('sistema') # Nombre clave
    sys_logger.setLevel(logging.INFO)
    if not sys_logger.handlers:
        sys_logger.addHandler(sys_handler)

    # --- 2. LOGGER DE AUDITORÍA (Acciones de usuarios, ediciones) ---
    audit_handler = RotatingFileHandler(auditoria_log, maxBytes=5*1024*1024, backupCount=3)
    audit_handler.setFormatter(audit_formatter) # <-- Aplicamos el formato limpio
    
    audit_logger = logging.getLogger('auditoria') # Nombre clave
    audit_logger.setLevel(logging.INFO)
    if not audit_logger.handlers:
        audit_logger.addHandler(audit_handler)

def create_app():

    setup_loggers()
    
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Ruta de almacenamiento apuntando al volumen de Docker para vol-app
    app.config['UPLOAD_FOLDER'] = '/storage_datos/storage-files'

    # Crea la carpeta automáticamente si no existe al arrancar la app
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    """Añade cabeceras para que el navegador no guarde en caché 
    páginas protegidas y fuerce la validación con el servidor."""

    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    from routers.auth import auth
    from routers.main import main

    app.register_blueprint(auth)
    app.register_blueprint(main)

    return app