from flask import Blueprint, render_template, redirect, url_for, session

main = Blueprint('main', __name__)


@main.route('/')
def home():
    if session.get('logged_in'):
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    return render_template('usuarios/dashboard.html', username=session.get('username'))