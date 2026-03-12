from flask import render_template, request, session, redirect, url_for, flash
from db.database_connector import get_db_connection
from datetime import datetime
import calendar
import logging

logger = logging.getLogger(__name__)

def user_mark_day_controller():
    if session.get('rol') != 'Administrador':
        flash("Acceso denegado.", "error")
        return redirect(url_for('main.home'))

    db = get_db_connection()
    if not db:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('main.home'))

    usuario_encontrado = None
    registros_mes = []
    
    busqueda = request.args.get('busqueda', '').strip()
    mes_str = request.args.get('mes', datetime.now().strftime('%Y-%m')) 

    try:
        anio_query, mes_query = map(int, mes_str.split('-'))
    except ValueError:
        ahora = datetime.now()
        anio_query, mes_query = ahora.year, ahora.month
        mes_str = f"{anio_query}-{mes_query:02d}"

    try:
        cursor = db.cursor(dictionary=True)

        if busqueda:
            sql_usuario = """
                SELECT u.id_usuario, u.nombres, u.apellidos, u.cedula, d.departamento
                FROM usuarios u
                JOIN departamentos d ON u.id_departamento = d.id_departamento
                WHERE u.cedula = %s OR CONCAT(u.nombres, ' ', u.apellidos) LIKE %s
                LIMIT 1
            """
            cursor.execute(sql_usuario, (busqueda, f"%{busqueda}%"))
            usuario_encontrado = cursor.fetchone()

            if usuario_encontrado:
                _, dias_en_mes = calendar.monthrange(anio_query, mes_query)
                fecha_inicio = f"{anio_query}-{mes_query:02d}-01"
                fecha_fin = f"{anio_query}-{mes_query:02d}-{dias_en_mes}"

                # Añadimos el estado_revision para pintar los colores correctos
                sql_registros = """
                    SELECT 
                        rd.fecha_registro,
                        rd.motivo_justificacion,
                        rd.detalle_justificacion,
                        rh.hora,
                        tm.codigo AS tipo_marcacion,
                        er.tipo AS estado_revision
                    FROM registro_dias rd
                    LEFT JOIN registro_horas rh ON rd.id_dias = rh.id_dias
                    LEFT JOIN tipos_marcacion tm ON rh.id_tipo_marcacion = tm.id_tipo
                    LEFT JOIN estados_revision er ON rh.id_estado_revision = er.id_estado
                    WHERE rd.id_usuario = %s AND rd.fecha_registro BETWEEN %s AND %s
                    ORDER BY rd.fecha_registro ASC, rh.hora ASC
                """
                cursor.execute(sql_registros, (usuario_encontrado['id_usuario'], fecha_inicio, fecha_fin))
                resultados_db = cursor.fetchall()

                dias_agrupados = {}
                for row in resultados_db:
                    fecha_str = row['fecha_registro'].strftime('%Y-%m-%d')
                    if fecha_str not in dias_agrupados:
                        dias_agrupados[fecha_str] = {
                            'fecha': fecha_str,
                            'marcaciones': [],
                            'justificacion': None
                        }
                    
                    if row['hora']:
                        dias_agrupados[fecha_str]['marcaciones'].append({
                            'hora': str(row['hora'])[:5],
                            'tipo': row['tipo_marcacion'],
                            'estado': row['estado_revision']
                        })

                    # Guardar justificación si existe
                    if row['motivo_justificacion']:
                        motivo = row['motivo_justificacion']
                        detalle = row['detalle_justificacion'] if row['detalle_justificacion'] else ""
                        dias_agrupados[fecha_str]['justificacion'] = f"{motivo} - {detalle}".strip(" -")

                # Convertir a lista ordenada
                registros_mes = [dias_agrupados[k] for k in sorted(dias_agrupados.keys())]

    except Exception as e:
        logger.error(f"Error en user_mark_day_controller: {e}")
        flash("Ocurrió un error al consultar la base de datos.", "error")
    finally:
        if 'cursor' in locals():
            cursor.close()
        db.close()

    return render_template(
        'users/user_mark_day.html',
        busqueda=busqueda,
        mes_seleccionado=mes_str,
        usuario=usuario_encontrado,
        registros=registros_mes
    )