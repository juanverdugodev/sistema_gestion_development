""" [EXPERIMENTAL] CONTROLADOR EXPERIMENTAL PARA ESCALABILIDAD """

from flask import render_template, session, request
from db.database_connector import get_db_connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def mark_day_controller():
    user_id = session.get('user_id')
    
    first_load = session.get('first_load_done', False)
    if not first_load:
        session['first_load_done'] = True
        show_global_anim = True
    else:
        show_global_anim = False

    ahora = datetime.now()
    
    # 1. Leer la fecha desde el buscador, si no existe, usar la de hoy
    fecha_param = request.args.get('fecha')
    if fecha_param:
        try:
            fecha_consulta = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except ValueError:
            fecha_consulta = ahora.date()
    else:
        fecha_consulta = ahora.date()

    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    nombre_dia = dias[fecha_consulta.weekday()]
    nombre_mes = meses[fecha_consulta.month - 1]

    fecha_display = f"{nombre_dia} {fecha_consulta.day} de {nombre_mes} de {fecha_consulta.year}".capitalize()
    
    # Textos formateados para el input del HTML
    hoy_str = ahora.strftime('%Y-%m-%d')
    fecha_seleccionada = fecha_consulta.strftime('%Y-%m-%d')
    
    registros_hoy = []
    observaciones = []
    tiene_novedades = False

    db = get_db_connection()
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            sql = """
                SELECT 
                    tm.codigo AS tipo, 
                    SUBSTRING(CAST(rh.hora AS CHAR), 1, 5) AS hora,
                    er.tipo AS estado_nombre
                FROM registro_dias rd
                JOIN registro_horas rh ON rd.id_dias = rh.id_dias
                JOIN tipos_marcacion tm ON rh.id_tipo_marcacion = tm.id_tipo
                JOIN estados_revision er ON rh.id_estado_revision = er.id_estado
                WHERE rd.id_usuario = %s AND rd.fecha_registro = %s
                ORDER BY rh.hora ASC
            """
            cursor.execute(sql, (user_id, fecha_consulta))
            query_results = cursor.fetchall()

            for row in query_results:
                estado = row['estado_nombre']
                
                registros_hoy.append({
                    'tipo': row['tipo'],
                    'hora': row['hora'],
                    'estado': estado
                })
                
                # Lógica de observaciones según el estado
                if estado == 'Anormal':
                    tiene_novedades = True
                    observaciones.append(f"Marcación de {row['tipo']} registrada como anormal.")
                elif estado == 'Pendiente':
                    tiene_novedades = True
                    observaciones.append(f"Marcación de {row['tipo']} se encuentra en revisión.")
                elif estado == 'Justificada':
                    # Opcional: Puedes decidir si 'Justificada' se considera novedad o no
                    observaciones.append(f"Marcación de {row['tipo']} ha sido justificada.")
                    
        except Exception as e:
            logger.error(f"Error en mark_day_controller: {e}")
        finally:
            cursor.close()
            db.close()

    return render_template(
        'users/mark_day.html',
        username=session.get('username'),
        show_global_anim=show_global_anim,
        fecha_actual=fecha_display,
        hoy_str=hoy_str,
        fecha_seleccionada=fecha_seleccionada,
        registros_hoy=registros_hoy,
        observaciones=observaciones,
        tiene_novedades=tiene_novedades
    )