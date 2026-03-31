from flask import render_template, redirect, url_for, session, request, flash
from werkzeug.security import generate_password_hash
from db.database_connector import get_db_connection
import logging
import re # Importamos la librería para usar Expresiones Regulares

logger = logging.getLogger(__name__)

def change_password_controller():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    error = None
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        check_password = request.form.get('check_password')
        
        # Expresión regular: Mínimo 8 chars, 1 mayúscula, 1 número, 1 especial de la lista permitida.
        # Bloquea espacios y caracteres fuera de este rango.
        regex_pattern = r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>/?])[A-Za-z\d!@#$%^&*()_+\-=\[\]{}|;:\'",.<>/?]{8,}$'
    
        if not new_password or not check_password:
            error = "Por favor, completa todos los campos."
        elif new_password != check_password:
            error = "Las contraseñas no coinciden."
        elif not re.match(regex_pattern, new_password):
            error = "La contraseña no cumple con los requisitos mínimos de seguridad."
        else:
            db = get_db_connection()
            try:
                cursor = db.cursor()
                # La función hash protege la base de datos sin importar el texto ingresado
                new_hash = generate_password_hash(new_password)
                sql = "UPDATE usuarios SET password_hash = %s, change_password = FALSE WHERE id_usuario = %s"
                cursor.execute(sql, (new_hash, session['user_id']))
                db.commit()
                
                # Acción crucial de seguridad
                session.clear() 
                flash("Contraseña actualizada con éxito. Inicia sesión nuevamente.")
                
                return redirect(url_for('auth.login'))
                
            except Exception as e:
                logger.exception(f"Error al cambiar clave: {e}")
                error = "Error al actualizar la clave. Inténtalo más tarde."
            finally:
                if db:
                    db.close()
                
    return render_template('users/change_password.html', 
                           username=session.get('username'), 
                           error=error)