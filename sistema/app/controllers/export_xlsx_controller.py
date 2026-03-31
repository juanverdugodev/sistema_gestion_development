import os
import io
import pandas as pd
import logging
import zipfile
from flask import render_template, request, jsonify, send_file, session
from openpyxl.utils import get_column_letter
from utils.file_manager import get_uploads_storage_parquet

# --- REEMPLAZO: Instanciamos los dos canales de logs ---
audit_logger = logging.getLogger('auditoria')
sys_logger = logging.getLogger('sistema')

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
        'users/audit/export_xlsx.html', 
        meses_disponibles=meses_disponibles,
        anios_disponibles=anios_disponibles
    )

def download_xlsx_controller():
    """Recibe la petición, convierte los Parquets a Excel en memoria, autoajusta columnas y los descarga."""
    mes_req = request.args.get('mes') 
    modo = request.args.get('modo', 'single') 
    
    # CORRECCIÓN: La llave correcta de la sesión es 'username', no 'usuario'
    usuario_actual = session.get('username', 'Usuario Desconocido') 

    if not mes_req:
        return jsonify({"error": "Mes no proporcionado"}), 400

    try:
        anio, mes = mes_req.split('-')
        nombre_carpeta = f"{mes}-{anio}"
        base_path = os.path.join(get_uploads_storage_parquet(), nombre_carpeta)

        # Ubicar los 3 posibles parquets
        ruta_1 = os.path.join(base_path, f"{nombre_carpeta}.parquet")
        ruta_2 = os.path.join(base_path, f"resumen-{nombre_carpeta}.parquet")
        ruta_3 = os.path.join(base_path, f"diario-{nombre_carpeta}.parquet")

        if not os.path.exists(ruta_1):
            return jsonify({"error": "No hay registros base para este mes."}), 404

        # Nombres dinámicos
        meses_nombres = {
            "01": "ENERO", "02": "FEBRERO", "03": "MARZO", "04": "ABRIL",
            "05": "MAYO", "06": "JUNIO", "07": "JULIO", "08": "AGOSTO",
            "09": "SEPTIEMBRE", "10": "OCTUBRE", "11": "NOVIEMBRE", "12": "DICIEMBRE"
        }
        nombre_mes = meses_nombres.get(mes, "MES")
        etiqueta_archivo = f"{nombre_mes}-{anio}"

        # Cargar los DataFrames 
        df1 = pd.read_parquet(ruta_1)
        df2 = pd.read_parquet(ruta_2) if os.path.exists(ruta_2) else None
        df3 = pd.read_parquet(ruta_3) if os.path.exists(ruta_3) else None

        # --- IGNORAR COLUMNA GRÁFICA EN EL EXCEL ---
        if df2 is not None and 'grafica' in df2.columns:
            df2 = df2.drop(columns=['grafica'])

        # --- FUNCIÓN: Autoajuste de ancho de columnas ---
        def autoajustar_columnas(writer_obj, nombre_hoja, dataframe):
            worksheet = writer_obj.sheets[nombre_hoja]
            for idx, col in enumerate(dataframe.columns):
                ancho_cabecera = len(str(col))
                if not dataframe.empty:
                    ancho_datos = dataframe[col].astype(str).str.len().max()
                else:
                    ancho_datos = 0
                if pd.isna(ancho_datos):
                    ancho_datos = 0
                ancho_final = max(ancho_cabecera, int(ancho_datos)) + 2
                worksheet.column_dimensions[get_column_letter(idx + 1)].width = ancho_final
        # ------------------------------------------------------

        if modo == 'single':
            # --- MODO 1: UN SOLO EXCEL CON 3 HOJAS ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df1.to_excel(writer, index=False, sheet_name='Registros')
                autoajustar_columnas(writer, 'Registros', df1)
                
                if df2 is not None: 
                    df2.to_excel(writer, index=False, sheet_name='Resumen mensual')
                    autoajustar_columnas(writer, 'Resumen mensual', df2)
                    
                if df3 is not None: 
                    df3.to_excel(writer, index=False, sheet_name='Resumen diario')
                    autoajustar_columnas(writer, 'Resumen diario', df3)
            
            output.seek(0)
            
            # LOG DE AUDITORÍA: Descarga de datos
            audit_logger.info(f"El usuario '{usuario_actual}' exporto los registros correspondientes al mes {mes}-{anio} en formato Excel unificado.")
            
            return send_file(
                output,
                download_name=f"ASISTENCIA-{etiqueta_archivo}.xlsx",
                as_attachment=True,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        elif modo == 'zip':
            # --- MODO 2: ARCHIVO ZIP CON 3 EXCELS SEPARADOS ---
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                
                def agregar_al_zip(df_to_save, nombre_archivo_excel):
                    if df_to_save is not None:
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_to_save.to_excel(writer, index=False, sheet_name='Datos')
                            autoajustar_columnas(writer, 'Datos', df_to_save)
                        zf.writestr(nombre_archivo_excel, excel_buffer.getvalue())

                agregar_al_zip(df1, f"REGISTROS-{etiqueta_archivo}.xlsx")
                agregar_al_zip(df2, f"RESUMEN-{etiqueta_archivo}.xlsx")
                agregar_al_zip(df3, f"DIARIO-{etiqueta_archivo}.xlsx")

            zip_buffer.seek(0)
            
            # LOG DE AUDITORÍA: Descarga de datos
            audit_logger.info(f"El usuario '{usuario_actual}' exporto los registros correspondientes al mes {mes}-{anio} en formato ZIP.")
            
            return send_file(
                zip_buffer,
                download_name=f"ASISTENCIA-{etiqueta_archivo}.zip",
                as_attachment=True,
                mimetype='application/zip'
            )

    except Exception as e:
        # LOG DE SISTEMA: Falla técnica al intentar procesar el Excel/Zip
        sys_logger.error(f"Error tecnico exportando Excel del mes {mes_req}: {e}")
        return jsonify({"error": str(e)}), 500