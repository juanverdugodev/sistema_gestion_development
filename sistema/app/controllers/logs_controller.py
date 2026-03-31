import os
from flask import render_template, jsonify
from utils.file_manager import get_logs_storage

def logs_page_controller():
    """Renderiza la página base del visor de logs"""
    return render_template('admin/logs_viewer.html')

def get_logs_api_controller(tipo_log):
    """
    Lee el archivo físico y devuelve las últimas líneas.
    tipo_log puede ser 'sistema' o 'auditoria'
    """
    # Evitar inyección de rutas limitando las opciones válidas
    if tipo_log not in ['sistema', 'auditoria']:
        return jsonify({"error": "Tipo de log no válido"}), 400
        
    log_filename = f"{tipo_log}.log"
    log_path = os.path.join(get_logs_storage(), log_filename)
    
    if not os.path.exists(log_path):
        return jsonify({"logs": []}), 200
        
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            
        # Tomamos las últimas 200 líneas
        ultimas_lineas = lineas[-200:]
        
        # Invertimos el orden para que lo más reciente salga arriba y limpiamos espacios
        logs_limpios = [linea.strip() for linea in reversed(ultimas_lineas) if linea.strip()]
        
        return jsonify({"logs": logs_limpios}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error leyendo archivo de logs: {str(e)}"}), 500