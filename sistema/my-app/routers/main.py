from flask import Blueprint, session, request, redirect, url_for, send_from_directory
from controllers.password_controller import change_password_controller
from controllers.home_controller import home_controller
from controllers.mark_day_controller import mark_day_controller
from controllers.generate_omr_controller import generate_format_omr
from controllers.upload_omr_controller import upload_page_controller, process_upload_controller, cancel_upload_controller, confirm_upload_controller
from controllers.profile_controller import view_profile_controller, update_profile_controller
from controllers.calendar_controller import calendar_controller
from controllers.user_mark_day_controller import user_mark_day_controller
from utils.file_manager import get_omr_storage
from utils.decorator import role_required


main = Blueprint('main', __name__)

@main.before_app_request
def check_password_status():
    if session.get('needs_password_change'):
        if request.endpoint not in ['main.change_password', 'auth.logout', 'static']:
            return redirect(url_for('main.change_password'))
        
@main.route('/')
def index():
    return redirect(url_for('main.home'))

@main.route('/home')
@role_required(['Administrador', 'Usuario']) 
def home():
    return home_controller()

@main.route('/profile', methods=['GET'])
@role_required(['Administrador', 'Usuario'])
def profile():
    return view_profile_controller()

@main.route('/profile/update', methods=['POST'])
@role_required(['Administrador', 'Usuario']) 
def update_profile():
    return update_profile_controller()

@main.route('/home/mark-day')
@role_required(['Administrador', 'Usuario']) 
def mark_day():
    return mark_day_controller()

@main.route('/home/calendar')
@role_required(['Administrador', 'Usuario'])
def view_calendar():
    return calendar_controller()

@main.route('/home/mark-day/preview-omr')
@role_required(['Administrador']) 
def preview_omr():
    return generate_format_omr()

@main.route('/home/mark-day/preview-omr/pdf/<filename>')
@role_required(['Administrador']) 
def serve_pdf_omr(filename):
    """Permite al iframe del frontend visualizar el PDF generado"""
    storage_path = get_omr_storage()
    return send_from_directory(storage_path, filename)

@main.route('/home/mark-day/upload-omr', methods=['GET'])
@role_required(['Administrador']) 
def upload_omr_view():
    """Ruta para mostrar la pantalla de carga del documento"""
    return upload_page_controller()

@main.route('/api/asistencia/upload-omr/process', methods=['POST'])
@role_required(['Administrador']) 
def process_upload_omr():
    """Ruta (API) que recibe el archivo desde el frontend vía AJAX/Fetch"""
    return process_upload_controller()

@main.route('/api/asistencia/upload-omr/cancel', methods=['POST'])
@role_required(['Administrador']) 
def cancel_upload_omr():
    return cancel_upload_controller()

@main.route('/api/asistencia/upload-omr/confirm', methods=['POST'])
@role_required(['Administrador']) 
def confirm_upload_omr():
    return confirm_upload_controller()

@main.route('/home/mark-day/user-records', methods=['GET'])
@role_required(['Administrador']) 
def admin_user_records():
    return user_mark_day_controller()

@main.route('/change_password', methods=['GET', 'POST'])
def change_password():
    return change_password_controller()
