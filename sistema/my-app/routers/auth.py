from flask import Blueprint, render_template, request, redirect, url_for, session

auth = Blueprint('auth', __name__)

USUARIO_ADMIN = "admin"
CONTRASENA_ADMIN = "123"


@auth.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == USUARIO_ADMIN and password == CONTRASENA_ADMIN:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('main.dashboard'))
        else:
            error = 'Usuario o contraseña incorrectos.'

    return render_template('login.html', error=error)


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))