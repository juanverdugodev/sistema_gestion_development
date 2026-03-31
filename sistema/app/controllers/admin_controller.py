from flask import request, redirect, url_for, session, flash, render_template
from db.database_connector import get_db_connection
from werkzeug.security import generate_password_hash
import logging

# Instanciamos los dos canales de logs que configuramos en app.py
audit_logger = logging.getLogger('auditoria')
sys_logger = logging.getLogger('sistema')

def check_admin_access():
    """Verifica que el usuario logueado sea del departamento Administrador de sistema."""
    if not session.get('logged_in'):
        return False
    if session.get('departamento') != 'Administrador de sistema':
        return False
    return True

class AdminController:
    @staticmethod
    def get_dashboard_data():
        db = get_db_connection()
        datos = {'usuarios': [], 'departamentos': [], 'roles': []}
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT id_departamento, departamento FROM departamentos")
                datos['departamentos'] = cursor.fetchall()
                
                cursor.execute("SELECT id_rol, rol_privilegio FROM roles_sistema")
                datos['roles'] = cursor.fetchall()
                
                cursor.execute("""
                    SELECT u.id_usuario, u.nombres, u.apellidos, u.cedula, u.id_departamento, 
                           u.id_rol, u.activo, u.change_password, d.departamento, r.rol_privilegio 
                    FROM usuarios u
                    JOIN departamentos d ON u.id_departamento = d.id_departamento
                    JOIN roles_sistema r ON u.id_rol = r.id_rol
                    ORDER BY u.apellidos ASC
                """)
                datos['usuarios'] = cursor.fetchall()
            except Exception as e:
                # Fallo técnico de BD -> Logger de Sistema
                sys_logger.error(f"Error al obtener datos admin en get_dashboard_data: {e}")
            finally:
                cursor.close()
                db.close()
        return datos

    @staticmethod
    def agregar_departamento(nombre):
        admin_actual = session.get('username', 'Usuario Desconocido') # Corregido
        db = get_db_connection()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO departamentos (departamento) VALUES (%s)", (nombre,))
                db.commit()
                flash('Departamento agregado exitosamente.', 'success')
                
                # Acción humana exitosa -> Logger de Auditoría
                audit_logger.info(f"El usuario '{admin_actual}' creó el nuevo departamento: '{nombre}'.")
                
            except Exception as e:
                db.rollback()
                # Error de ejecución -> Logger de Sistema
                sys_logger.error(f"Fallo de BD al intentar agregar departamento '{nombre}': {e}")
                flash('Error al agregar departamento. Puede que ya exista.', 'error')
            finally:
                cursor.close()
                db.close()

    @staticmethod
    def agregar_usuario(nombres, apellidos, cedula, id_departamento, id_rol):
        admin_actual = session.get('username', 'Usuario Desconocido')
        db = get_db_connection()
        if db:
            try:
                cursor = db.cursor()
                pwd_hash = generate_password_hash('Default1', method='pbkdf2:sha256')
                
                sql = """INSERT INTO usuarios (nombres, apellidos, cedula, password_hash, 
                         id_departamento, id_rol, change_password, activo) 
                         VALUES (%s, %s, %s, %s, %s, %s, 1, 1)"""
                cursor.execute(sql, (nombres, apellidos, cedula, pwd_hash, id_departamento, id_rol))
                db.commit()
                flash('Usuario creado con éxito. Contraseña temporal: Default1', 'success')
                
                # Acción humana exitosa -> Logger de Auditoría
                audit_logger.info(f"El usuario '{admin_actual}' registró al nuevo funcionario '{nombres} {apellidos}' (C.I: {cedula}).")
                
            except Exception as e:
                db.rollback()
                # Error de ejecución -> Logger de Sistema
                sys_logger.error(f"Fallo de BD al intentar crear al usuario '{nombres} {apellidos}' (C.I: {cedula}): {e}")
                flash('Error al crear el usuario. Verifique si la cédula ya existe.', 'error')
            finally:
                cursor.close()
                db.close()

    @staticmethod
    def editar_usuario(id_usuario, nombres, apellidos, cedula, id_departamento, id_rol):
        admin_actual = session.get('username', 'Usuario Desconocido') # Corregido
        db = get_db_connection()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT id_usuario FROM usuarios WHERE cedula = %s AND id_usuario != %s", (cedula, id_usuario))
                if cursor.fetchone():
                    flash('La cédula ingresada ya pertenece a otro usuario.', 'error')
                    return

                sql = """UPDATE usuarios SET nombres=%s, apellidos=%s, cedula=%s, 
                         id_departamento=%s, id_rol=%s WHERE id_usuario=%s"""
                cursor.execute(sql, (nombres, apellidos, cedula, id_departamento, id_rol, id_usuario))
                db.commit()
                flash('Usuario actualizado correctamente.', 'success')
                
                # Acción humana exitosa -> Logger de Auditoría
                audit_logger.info(f"El usuario '{admin_actual}' editó la información del funcionario '{nombres} {apellidos}' (ID: {id_usuario}, C.I: {cedula}).")

            except Exception as e:
                db.rollback()
                # Error de ejecución -> Logger de Sistema
                sys_logger.error(f"Fallo de BD al intentar actualizar al usuario ID {id_usuario}: {e}")
                flash('Error al actualizar el usuario.', 'error')
            finally:
                cursor.close()
                db.close()

    @staticmethod
    def resetear_password(id_usuario):
        admin_actual = session.get('username', 'Usuario Desconocido') # Corregido
        db = get_db_connection()
        if db:
            try:
                cursor = db.cursor()
                
                # Obtenemos el nombre del afectado para que el log sea legible
                cursor.execute("SELECT nombres, apellidos FROM usuarios WHERE id_usuario=%s", (id_usuario,))
                user_data = cursor.fetchone()
                nombre_afectado = f"{user_data[0]} {user_data[1]}" if user_data else f"ID {id_usuario}"
                
                pwd_hash = generate_password_hash('Default1', method='pbkdf2:sha256')
                sql = "UPDATE usuarios SET password_hash=%s, change_password=1 WHERE id_usuario=%s"
                cursor.execute(sql, (pwd_hash, id_usuario))
                db.commit()
                flash('Contraseña restablecida a "Default1". El usuario deberá cambiarla al ingresar.', 'success')
                
                # Acción humana crítica (Seguridad) -> Logger de Auditoría sin Emojis
                audit_logger.warning(f"ACCION CRITICA: El usuario '{admin_actual}' reseteo la contraseña del funcionario '{nombre_afectado}' (ID: {id_usuario}) al valor por defecto.")

            except Exception as e:
                db.rollback()
                # Error de ejecución -> Logger de Sistema
                sys_logger.error(f"Fallo de BD al intentar resetear la contraseña del usuario ID {id_usuario}: {e}")
                flash('Error al restablecer la contraseña.', 'error')
            finally:
                cursor.close()
                db.close()

# CONTROLADORES EXPORTADOS PARA MAIN.PY

def admin_usuarios_controller():
    if not check_admin_access():
        # Intento de acceso no autorizado -> Logger de Auditoría/Seguridad
        audit_logger.warning(f"Intento de acceso denegado al Panel de Administracion por el usuario '{session.get('username', 'Usuario Desconocido')}'.")
        flash('Acceso denegado. Exclusivo para el Administrador de sistema.', 'error')
        return redirect(url_for('main.home'))
    
    datos = AdminController.get_dashboard_data()
    return render_template('admin/admin_panel.html', datos=datos)

def nuevo_departamento_controller():
    if check_admin_access() and request.method == 'POST':
        nombre = request.form.get('departamento', '').strip()
        if nombre:
            AdminController.agregar_departamento(nombre)
    return redirect(url_for('main.admin_gestion_usuarios'))

def nuevo_usuario_controller():
    if check_admin_access() and request.method == 'POST':
        AdminController.agregar_usuario(
            request.form.get('nombres'), request.form.get('apellidos'),
            request.form.get('cedula'), request.form.get('id_departamento'), request.form.get('id_rol')
        )
    return redirect(url_for('main.admin_gestion_usuarios'))

def editar_usuario_controller():
    if check_admin_access() and request.method == 'POST':
        AdminController.editar_usuario(
            request.form.get('id_usuario'), request.form.get('nombres'),
            request.form.get('apellidos'), request.form.get('cedula'),
            request.form.get('id_departamento'), request.form.get('id_rol')
        )
    return redirect(url_for('main.admin_gestion_usuarios'))

def reset_password_admin_controller():
    if check_admin_access() and request.method == 'POST':
        AdminController.resetear_password(request.form.get('id_usuario'))
    return redirect(url_for('main.admin_gestion_usuarios'))