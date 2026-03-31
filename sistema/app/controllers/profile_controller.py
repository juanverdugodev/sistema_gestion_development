from flask import render_template, request, redirect, url_for, session, flash
from db.database_connector import get_db_connection
import logging

logger = logging.getLogger(__name__)

def view_profile_controller():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    db = get_db_connection()
    user_data = None
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            # Consultamos los datos frescos directamente de la base de datos
            sql = """
                SELECT u.nombres, u.apellidos, u.cedula, r.rol_privilegio, d.departamento 
                FROM usuarios u
                JOIN roles_sistema r ON u.id_rol = r.id_rol
                JOIN departamentos d ON u.id_departamento = d.id_departamento
                WHERE u.id_usuario = %s
            """
            cursor.execute(sql, (session.get('user_id'),))
            user_data = cursor.fetchone()
        except Exception as e:
            logger.error(f"Error al obtener perfil: {e}")
            flash("Error al cargar la información del perfil.", "error")
        finally:
            cursor.close()
            db.close()

    return render_template('users/profile.html', user=user_data)

def update_profile_controller():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        cedula = request.form.get('cedula', '').strip()
        user_id = session.get('user_id')

        if not nombres or not apellidos or not cedula:
            flash('Nombres, apellidos y cédula son obligatorios.', 'error')
            return redirect(url_for('main.profile'))

        db = get_db_connection()
        if db:
            try:
                cursor = db.cursor()
                
                # 1. COMPROBACIÓN PREVIA: Verificar si la cédula ya existe en OTRO usuario
                # Usamos id_usuario != %s para permitirle al usuario guardar si no cambió su propia cédula
                sql_check = "SELECT id_usuario FROM usuarios WHERE cedula = %s AND id_usuario != %s"
                cursor.execute(sql_check, (cedula, user_id))
                existe_cedula = cursor.fetchone()
                
                if existe_cedula:
                    # Si encuentra un registro, bloqueamos la actualización y avisamos
                    flash('El número de cédula ingresado ya se encuentra registrado en otra cuenta.', 'error')
                    return redirect(url_for('main.profile'))

                # 2. ACTUALIZACIÓN: Si pasa el filtro, procedemos a guardar
                sql_update = "UPDATE usuarios SET nombres = %s, apellidos = %s, cedula = %s WHERE id_usuario = %s"
                cursor.execute(sql_update, (nombres, apellidos, cedula, user_id))
                db.commit()
                
                # Actualizamos la sesión para que el nombre cambie instantáneamente en la barra superior
                session['username'] = f"{nombres} {apellidos}"
                
                # Mensaje de éxito solicitado
                flash('Datos actualizados correctamente.', 'success')
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error al actualizar perfil: {e}")
                flash('Ocurrió un error al intentar actualizar el perfil.', 'error')
            finally:
                cursor.close()
                db.close()

    return redirect(url_for('main.profile'))