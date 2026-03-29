""" [EXPERIMENTAL] CONTROLADOR EXPERIMENTAL PARA ESCALABILIDAD """

from flask import render_template, session, request
from db.database_connector import get_db_connection
from datetime import date, timedelta
import calendar
import locale
import logging

logger = logging.getLogger(__name__)

def calendar_controller():
    # Configurar idioma
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252') 
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'esp')
        except locale.Error:
            pass 

    usuario_id = session.get('user_id')
    hoy = date.today()

    # 1. Determinar el mes y año a mostrar (por defecto, el actual)
    try:
        mes_query = int(request.args.get('mes', hoy.month))
        anio_query = int(request.args.get('anio', hoy.year))
    except ValueError:
        mes_query = hoy.month
        anio_query = hoy.year

    # Validar rangos básicos
    if mes_query < 1 or mes_query > 12:
        mes_query = hoy.month
        anio_query = hoy.year

    # 2. Calcular datos del mes
    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    nombre_mes_actual = f"{meses_nombres[mes_query - 1]} {anio_query}"

    # Fechas de inicio y fin del mes para la consulta SQL
    _, dias_en_mes = calendar.monthrange(anio_query, mes_query)
    fecha_inicio_mes = date(anio_query, mes_query, 1)
    fecha_fin_mes = date(anio_query, mes_query, dias_en_mes)

    # 3. Consultar días marcados en la base de datos
    fechas_marcadas = set()
    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            # Buscamos todos los registros del usuario en este mes
            sql = """
                SELECT fecha_registro 
                FROM registro_dias 
                WHERE id_usuario = %s AND fecha_registro BETWEEN %s AND %s
            """
            cursor.execute(sql, (usuario_id, fecha_inicio_mes, fecha_fin_mes))
            resultados = cursor.fetchall()
            
            for fila in resultados:
                fecha_db = fila[0]
                if isinstance(fecha_db, date):
                    fechas_marcadas.add(fecha_db.strftime('%Y-%m-%d'))
                else:
                    fechas_marcadas.add(str(fecha_db))
    except Exception as e:
        logger.error(f"Error al consultar el calendario mensual: {e}")
    finally:
        if conexion:
            conexion.close()

    # 4. Construir la estructura del calendario
    cal = calendar.Calendar(firstweekday=0) # 0 = Lunes
    mes_calendario = cal.monthdatescalendar(anio_query, mes_query)
    
    semanas = []
    for semana in mes_calendario:
        dias_semana = []
        for dia in semana:
            str_fecha = dia.strftime('%Y-%m-%d')
            dias_semana.append({
                "fecha": str_fecha,
                "numero": dia.day,
                "es_mes_actual": dia.month == mes_query,
                "es_fin_semana": dia.weekday() >= 5,
                "es_hoy": dia == hoy,
                "marcado": str_fecha in fechas_marcadas
            })
        semanas.append(dias_semana)

    # Controles de navegación (Mes anterior y siguiente)
    mes_anterior = mes_query - 1 if mes_query > 1 else 12
    anio_anterior = anio_query if mes_query > 1 else anio_query - 1
    
    mes_siguiente = mes_query + 1 if mes_query < 12 else 1
    anio_siguiente = anio_query if mes_query < 12 else anio_query + 1

    return render_template(
        'users/calendar.html',
        nombre_mes_actual=nombre_mes_actual,
        semanas=semanas,
        mes_anterior=mes_anterior,
        anio_anterior=anio_anterior,
        mes_siguiente=mes_siguiente,
        anio_siguiente=anio_siguiente
    )