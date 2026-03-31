from flask import Blueprint, session, request, redirect, url_for, send_from_directory
from controllers.password_controller import change_password_controller
from controllers.home_controller import home_controller
from controllers.mark_day_controller import mark_day_controller
from controllers.generate_omr_controller import generate_format_omr
from controllers.upload_omr_controller import upload_page_controller, process_upload_controller, cancel_upload_controller, confirm_upload_controller
from controllers.profile_controller import view_profile_controller, update_profile_controller
from controllers.calendar_controller import calendar_controller
from controllers.user_mark_day_records_controller import obtener_nombres_parquet, validar_marcaciones, guardar_edicion_jornada_api
from controllers.upload_xlsx_controller import upload_xlsx_page_controller, process_upload_xlsx_controller, cancel_upload_xlsx_controller, confirm_upload_xlsx_controller
from controllers.export_xlsx_controller import export_xlsx_page_controller, download_xlsx_controller
from controllers.logs_controller import logs_page_controller, get_logs_api_controller
from utils.file_manager import get_omr_storage
from utils.decorator import role_required

# IMPORTS PARA EL PANEL DE ADMINISTRACIÓN
from controllers.admin_controller import (
    admin_usuarios_controller, 
    nuevo_departamento_controller, 
    nuevo_usuario_controller, 
    editar_usuario_controller, 
    reset_password_admin_controller
)

main = Blueprint('main', __name__)

 # Endpoint para el cambio de clave en primer inicio de sesion
@main.before_app_request
def check_password_status():
    if session.get('needs_password_change'):
        if request.endpoint not in ['main.change_password', 'auth.logout', 'static']:
            return redirect(url_for('main.change_password'))
        
@main.route('/')
def index():
    if session.get('rol') == 'Administrador':
        return redirect(url_for('main.admin_user_records'))
    return redirect(url_for('main.home'))

 # ENDPOINTS EXPERIMENTALES / ESCALABLES  < -------------------------
@main.route('/home')
@role_required(['Administrador', 'Usuario']) 
def home():
    return home_controller()

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

# ----------------------------------------------------------------------

# ENDPOINTS PRINCIPALES:  < ----------------------------

@main.route('/profile', methods=['GET'])
@role_required(['Administrador', 'Usuario'])
def profile():
    return view_profile_controller()

@main.route('/profile/update', methods=['POST'])
@role_required(['Administrador', 'Usuario']) 
def update_profile():
    return update_profile_controller()

@main.route('/home/mark-day/user-records', methods=['GET'])
@role_required(['Administrador']) 
def admin_user_records():
    # Ruta principal que renderiza la vista y la tabla
    return validar_marcaciones()

@main.route('/api/records/get-names', methods=['GET'])
@role_required(['Administrador'])
def get_names_by_month_api():
    # API invocada por Alpine.js para llenar el selector de nombres dinámicamente
    return obtener_nombres_parquet()

@main.route('/api/guardar_edicion_jornada', methods=['POST'])
@role_required(['Administrador'])
def guardar_edicion_jornada():
    # API invocada por el botón "Aplicar cambios" para sobrescribir el Parquet
    return guardar_edicion_jornada_api()


# Endpoints para carga de archivos .xlsx
@main.route('/home/mark-day/upload-xlsx', methods=['GET'])
@role_required(['Administrador']) 
def upload_xlsx_view():
    return upload_xlsx_page_controller()

@main.route('/api/register/upload-xlsx/process', methods=['POST'])
@role_required(['Administrador']) 
def process_upload_xlsx():
    return process_upload_xlsx_controller()

@main.route('/api/register/upload-xlsx/cancel', methods=['POST'])
@role_required(['Administrador']) 
def cancel_upload_xlsx():
    return cancel_upload_xlsx_controller()

@main.route('/api/register/upload-xlsx/confirm', methods=['POST'])
@role_required(['Administrador']) 
def confirm_upload_xlsx():
    return confirm_upload_xlsx_controller()

# Endpoints para EXPORTAR archivos .xlsx
@main.route('/home/export-xlsx', methods=['GET'])
@role_required(['Administrador']) 
def export_xlsx_view():
    return export_xlsx_page_controller()

@main.route('/api/records/download-xlsx', methods=['GET'])
@role_required(['Administrador']) 
def download_xlsx_api():
    return download_xlsx_controller()

# ENDPOINTS: PANEL DE ADMINISTRACIÓN SISTEMA (Usuarios y Departamentos)

@main.route('/admin/manage-user', methods=['GET'])
@role_required(['Administrador']) 
def admin_gestion_usuarios():
    return admin_usuarios_controller()

@main.route('/api/admin/department/new', methods=['POST'])
@role_required(['Administrador'])
def nuevo_departamento():
    return nuevo_departamento_controller()

@main.route('/api/admin/user/new', methods=['POST'])
@role_required(['Administrador'])
def nuevo_usuario():
    return nuevo_usuario_controller()

@main.route('/api/admin/user/edit', methods=['POST'])
@role_required(['Administrador'])
def editar_usuario():
    return editar_usuario_controller()

@main.route('/api/admin/user/reset-password', methods=['POST'])
@role_required(['Administrador'])
def reset_password_admin():
    return reset_password_admin_controller()

# --- ENDPOINTS: VISOR DE LOGS Y AUDITORÍA ---
@main.route('/admin/logs', methods=['GET'])
@role_required(['Administrador'])
def admin_logs_view():
    """Página principal del visor de logs"""
    return logs_page_controller()

@main.route('/api/admin/logs/<tipo>', methods=['GET'])
@role_required(['Administrador'])
def api_get_logs(tipo):
    """API que devuelve el JSON de auditoría o sistema"""
    return get_logs_api_controller(tipo)

# ----------------------------------------------------

# Enpoint para el cambio de password
@main.route('/change_password', methods=['GET', 'POST'])
def change_password():
    return change_password_controller()
