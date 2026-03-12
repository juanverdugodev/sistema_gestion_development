from flask import Blueprint
from controllers.auth_controller import login_controller, logout_controller

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    return login_controller()

@auth.route('/logout')
def logout():
    return logout_controller()