import os
import io
import pandas as pd
import logging
from flask import render_template, request, jsonify, send_file
from utils.file_manager import get_uploads_storage_parquet

logger = logging.getLogger(__name__)

def export_xlsx_page_controller():
    """Renderiza la vista principal con los meses disponibles."""
    storage = get_uploads_storage_parquet()
    meses_disponibles = []
    anios_disponibles = set()

    meses_nombres = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }

    if os.path.exists(storage):
        for folder in os.listdir(storage):
            if "-" in folder:
                mes, anio = folder.split("-")
                if mes in meses_nombres:
                    meses_disponibles.append({"num": mes, "nombre": meses_nombres[mes]})
                    anios_disponibles.add(anio)

    # Eliminar duplicados y ordenar
    meses_disponibles = [dict(t) for t in {tuple(d.items()) for d in meses_disponibles}]
    meses_disponibles = sorted(meses_disponibles, key=lambda x: x['num'])
    anios_disponibles = sorted(list(anios_disponibles))

    return render_template(
        'users/export_xlsx.html', 
        meses_disponibles=meses_disponibles,
        anios_disponibles=anios_disponibles
    )

def download_xlsx_controller():
    """Recibe la petición, convierte el Parquet a Excel en memoria y lo descarga."""
    mes_req = request.args.get('mes') # Ej: "2026-03"

    if not mes_req:
        return jsonify({"error": "Mes no proporcionado"}), 400

    try:
        anio, mes = mes_req.split('-')
        nombre_carpeta = f"{mes}-{anio}"
        ruta_archivo = os.path.join(get_uploads_storage_parquet(), nombre_carpeta, f"{nombre_carpeta}.parquet")

        if not os.path.exists(ruta_archivo):
            return jsonify({"error": "No hay registros para este mes."}), 404

        # 1. Leer el Parquet
        df = pd.read_parquet(ruta_archivo)

        # 2. Diccionario para el nombre dinámico del archivo
        meses_nombres = {
            "01": "ENERO", "02": "FEBRERO", "03": "MARZO", "04": "ABRIL",
            "05": "MAYO", "06": "JUNIO", "07": "JULIO", "08": "AGOSTO",
            "09": "SEPTIEMBRE", "10": "OCTUBRE", "11": "NOVIEMBRE", "12": "DICIEMBRE"
        }
        nombre_mes = meses_nombres.get(mes, "MES")
        filename = f"REGISTROS-ASISTENCIA-{nombre_mes}-{anio}.xlsx"

        # 3. Crear el Excel en memoria RAM (sin escribir en el disco)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Asistencia')

        output.seek(0) # Regresar el puntero al inicio del archivo en memoria

        # 4. Enviar directamente como descarga
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error(f"Error exportando Excel: {e}")
        return jsonify({"error": str(e)}), 500