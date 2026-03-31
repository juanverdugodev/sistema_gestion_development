from functools import wraps
from flask import session, redirect, url_for, flash, request

def role_required(roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('auth.login'))
            
            # Verificamos el rol actual
            rol_actual = session.get('rol')
            
            # Si el rol del usuario no está en la lista permitida o está vacío
            if rol_actual not in roles_permitidos:
                flash("No tienes permisos para acceder a esta sección.", "warning")
                
                # PREVENCIÓN DE BUCLE: Si está intentando entrar al home o no tiene rol, forzamos logout
                if request.endpoint == 'main.home' or not rol_actual:
                    return redirect(url_for('auth.logout'))
                
                # Si está en otra página, lo devolvemos al home
                return redirect(url_for('main.home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator