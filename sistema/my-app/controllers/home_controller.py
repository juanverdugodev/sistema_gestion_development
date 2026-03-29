""" [EXPERIMENTAL] CONTROLADOR EXPERIMENTAL PARA ESCALABILIDAD """

from flask import render_template, session
from db.database_connector import get_db_connection
from datetime import date, timedelta
import locale
import logging
logging.basicConfig(level=logging.INFO)

def home_controller():
    # Configurar idioma para que los meses salgan en español (Ajustado para Windows)
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252') 
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'esp')
        except locale.Error:
            pass # Si falla, usará el idioma por defecto del sistema

    hoy = date.today()
    
    usuario_id = session.get('user_id') 

    # 1. Obtener Mes y Año actual (Ej: "Marzo 2026")
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_anio = f"{meses[hoy.month - 1]} {hoy.year}"

    # 2. Calcular el rango de la semana (Lunes a Domingo)
    inicio_semana = hoy - timedelta(days=hoy.weekday()) # Lunes de esta semana
    fin_semana = inicio_semana + timedelta(days=6)      # Domingo de esta semana

    # 3. Consulta a la base de datos (MySQL)
    fechas_marcadas = set()
    conexion = None
    
    try:
        conexion = get_db_connection() # <-- REEMPLAZA ESTO por tu función real de conexión
        with conexion.cursor() as cursor:
            sql = """
                SELECT fecha_registro 
                FROM registro_dias 
                WHERE id_usuario = %s AND fecha_registro BETWEEN %s AND %s
            """
            cursor.execute(sql, (usuario_id, inicio_semana, fin_semana))
            resultados = cursor.fetchall()
            
            for fila in resultados:
                fecha_db = fila[0]
                if isinstance(fecha_db, date):
                    fechas_marcadas.add(fecha_db.strftime('%Y-%m-%d'))
                else:
                    fechas_marcadas.add(str(fecha_db))
                    
    except Exception as e:
        logging.error(f"Error al consultar el resumen semanal: {e}")
    finally:
        if conexion:
            conexion.close()

    nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dias_semana = []

    for i in range(7):
        fecha_iteracion = inicio_semana + timedelta(days=i)
        str_fecha = fecha_iteracion.strftime('%Y-%m-%d')
        
        dias_semana.append({
            "nombre": nombres_dias[i],
            "numero": fecha_iteracion.day,
            "es_fin_semana": i >= 5, # i=5 es Sábado, i=6 es Domingo
            "es_hoy": fecha_iteracion == hoy,
            "marcado": str_fecha in fechas_marcadas
        })

    return render_template('users/home.html', mes_anio=mes_anio, dias_semana=dias_semana)