from flask import render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from db.database_connector import get_db_connection
import logging

# --- REEMPLAZO: Instanciamos los dos canales de logs ---
audit_logger = logging.getLogger('auditoria')
sys_logger = logging.getLogger('sistema')

def login_controller():
    if session.get('logged_in'):
        if session.get('rol') == 'Administrador':
            return redirect(url_for('main.admin_user_records'))
        return redirect(url_for('main.home'))
    
    error = None
    if request.method == 'POST':
        raw_input = request.form['username'].strip()
        login_input_upper = raw_input.upper()
        password = request.form['password']
        
        db = get_db_connection()
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                sql = """
                    SELECT u.id_usuario, u.id_rol, u.nombres, u.apellidos, u.cedula, u.password_hash, u.activo, u.change_password, r.rol_privilegio, d.departamento  
                    FROM usuarios u
                    JOIN roles_sistema r ON u.id_rol = r.id_rol
                    JOIN departamentos d ON u.id_departamento = d.id_departamento
                    WHERE u.cedula = %s 
                    OR UPPER(CONCAT(u.nombres, ' ', u.apellidos)) = %s
                    LIMIT 1
                """
                cursor.execute(sql, (raw_input, login_input_upper))
                user = cursor.fetchone()

                if user:
                    if not user['activo']:
                        # LOG DE AUDITORÍA: Intento de acceso de cuenta inactiva (Alerta de seguridad)
                        nombre_inactivo = f"{user['nombres']} {user['apellidos']}"
                        audit_logger.warning(f"Intento de inicio de sesion bloqueado: El usuario '{nombre_inactivo}' (ID {user['id_usuario']}) intento acceder pero su cuenta esta desactivada.")
                        error = 'Su cuenta está desactivada. Contacte al administrador.'
                    elif check_password_hash(user['password_hash'], password):
                        session.clear()
                        session['user_id'] = user['id_usuario']
                        session['rol_id'] = user['id_rol'] # Para validaciones internas (como el OMR)
                        session['rol'] = user['rol_privilegio']
                        session['username'] = f"{user['nombres']} {user['apellidos']}"
                        session['departamento'] = user['departamento']

                        if user['change_password']:
                            session['needs_password_change'] = True
                            return redirect(url_for('main.change_password'))
                        
                        session['logged_in'] = True
                        if session['rol'] == 'Administrador':
                            return redirect(url_for('main.admin_user_records'))
                        else:
                            return redirect(url_for('main.home'))
                    else:
                        error = 'Usuario o contraseña incorrectos.'
                else:
                    error = 'Usuario o contraseña incorrectos.'
            except Exception as e:
                # LOG DE SISTEMA: Falla en el código o en la consulta SQL
                sys_logger.exception(f"Error en login: {e}")
                error = "Error interno del servidor."
            finally:
                cursor.close()
                db.close()
        else:
            # LOG DE SISTEMA: Falla de conexión a la base de datos
            sys_logger.error(f"Error (Def login()) base de datos.")
            error = "No hay conexión con la base de datos."
            
    return render_template('auth/login.html', error=error)

def logout_controller():
    session.clear()
    return redirect(url_for('auth.login'))