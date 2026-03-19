from flask import render_template, request, session, redirect, url_for, flash, jsonify
from utils.file_manager import get_uploads_storage_parquet
from datetime import datetime
import logging
import os
import pandas as pd
import uuid
import re

logger = logging.getLogger(__name__)


# ESCANEO DE ARCHIVOS (MESES Y AÑOS DINÁMICOS) PARA EL CAMPO SELECT HTML

def obtener_filtros_disponibles():
    """Escanea la carpeta de parquets y devuelve listas de meses y años existentes."""
    folder = get_uploads_storage_parquet()
    anios = set()
    meses_num = set()
    
    if os.path.exists(folder):
        for filename in os.listdir(folder):
            # Regex atrapa el mes (grupo 1) y el año (grupo 2) -> Ej: 09-2024
            match = re.match(r"(\d{2})-(\d{4})\.parquet", filename)
            if match:
                meses_num.add(match.group(1))
                anios.add(match.group(2))
                
    # Traductor de meses para el HTML
    nombres_meses = {
        '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
        '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
        '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
    }

    # Empaquetamos los meses: [{'num': '09', 'nombre': 'Septiembre'}, ...]
    meses_final = [{'num': m, 'nombre': nombres_meses[m]} for m in sorted(list(meses_num))]
    anios_final = sorted(list(anios))
    
    return meses_final, anios_final

# API: LLENAR SELECTOR DE NOMBRES

def obtener_nombres_parquet():
    """Devuelve los nombres únicos de un mes específico para el selector HTML."""
    mes_req = request.args.get('mes')
    
    if not mes_req:
        return jsonify({"exists": False, "names": []}), 200

    try:
        anio, mes = mes_req.split('-')
        ruta_archivo = os.path.join(get_uploads_storage_parquet(), f"{mes}-{anio}.parquet")

        if not os.path.exists(ruta_archivo):
            return jsonify({"exists": False, "names": []}), 200

        df = pd.read_parquet(ruta_archivo)
        nombres_unicos = df['nombre'].dropna().unique().tolist()
        
        # Responde con un JSON: {"exists": true, "names": ["Admin Admin", "Juan..."]}
        return jsonify({"exists": True, "names": sorted(nombres_unicos)}), 200
        
    except Exception as e:
        logger.error(f"Error al obtener nombres: {e}")
        return jsonify({"exists": False, "names": [], "error": str(e)}), 500



# FUNCIÓN PRINCIPAL: CONSULTA DE MARCACIONES

def validar_marcaciones():
    """Dibuja la pantalla y procesa las marcaciones si se envían filtros."""
    
    # --- PASO 1: Seguridad y Captura de Parámetros ---
    if session.get('rol') != 'Administrador':
        flash("Acceso denegado.", "error")
        return redirect(url_for('main.home'))

    empleado_req = request.args.get('busqueda', '').strip() 
    mes_req = request.args.get('mes', '')               

    # --- PASO 2: Variables de Respuesta (Vacías por defecto) ---
    datos_usuario = None
    semanas_finales = []

    # Genera: {'2026-03-05': [{'hora': '08:00', 'tipo': 'Entrada'...}, ...]}
    marcas_json = {} # Diccionario para Alpine.js

    # Escaneamos la carpeta real para llenar los desplegables de selección
    lista_meses, lista_anios = obtener_filtros_disponibles()

    # Si la carpeta está completamente vacía y apenas entramos a la página
    if not lista_anios and not mes_req and not empleado_req:
        flash("No existen registros cargados en el sistema, dirigete a la seccion de cargar registros.", "error")

    # --- PASO 3: Validación y Lectura de Archivo ---
    if mes_req:
        try:
            anio, mes = mes_req.split('-')
            ruta_archivo = os.path.join(get_uploads_storage_parquet(), f"{mes}-{anio}.parquet")

            if not os.path.exists(ruta_archivo):
                flash(f"No existen registros para {mes}-{anio}.", "error")
            else:
                df_total = pd.read_parquet(ruta_archivo)

                # --- PASO 4: Filtrar datos del empleado ---
                df_emp = df_total[df_total['nombre'] == empleado_req].copy()

                if df_emp.empty:
                    flash(f"No hay registros de {empleado_req} en este mes.", "warning")

                else:
                    # Ordenar fechas cronológicamente
                    df_emp['fecha_hora'] = pd.to_datetime(df_emp['fecha_hora'])
                    df_emp = df_emp.sort_values(by='fecha_hora')

                    # --- PASO 5: Extraer Perfil del Usuario ---
                    info_base = df_emp.iloc[0]
                    datos_usuario = {
                        'nombres': empleado_req, # Usamos un solo campo de nombre
                        'cedula': str(info_base.get('cedula', 'N/A')),
                        'departamento': str(info_base.get('departamento', 'N/A'))
                    }

                    # Contamos el total de registros y los días únicos
                    total_registros = len(df_emp)
                    total_dias = df_emp['fecha_hora'].dt.date.nunique()

                    flash(f"Se encontraron {total_dias} días con {total_registros} registros para el funcionario {empleado_req}.", "success")

                    # --- PASO 6: Agrupar por Días ---
                    nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    
                    # Diccionario donde agruparemos las marcas. Llave = '2026-03-05', Valor = Diccionario con info del día
                    calendario_mes = {}

                    # Iteramos sobre cada fila del DataFrame del empleado (SIN MODIFICAR EL DF)
                    for _, fila_marca in df_emp.iterrows():
                        if pd.notna(fila_marca['fecha_hora']):
                            # Extraemos componentes de la fecha
                            fecha_limpia = fila_marca['fecha_hora'].date()          # Ej: datetime.date(2026, 3, 5)
                            fecha_texto = fecha_limpia.strftime('%Y-%m-%d')         # Ej: '2026-03-05'
                            hora_texto = fila_marca['fecha_hora'].strftime('%H:%M') # Ej: '08:30'

                            # Si el día aún no existe en nuestro calendario, lo creamos
                            if fecha_texto not in calendario_mes:
                                calendario_mes[fecha_texto] = {
                                    'fecha': fecha_texto,
                                    'fecha_obj': fecha_limpia, 
                                    'dia_semana': nombres_dias[fecha_limpia.weekday()],
                                    'marcaciones': [],    # Aquí meteremos la lista de marcas
                                    'estados_dia': set()  # Usamos un Set temporal para evitar etiquetas duplicadas
                                }
                            
                            # Extraemos información específica de esta fila/marca
                            metodo_ingreso = fila_marca.get('verificacion', 'SISTEMA')
                            tipo_evento = fila_marca.get('tipoMarcacion', fila_marca.get('tipoMarcacion', 'Registro'))
                            
                            # Construimos el diccionario de la marca individual
                            marca_individual = {
                                'id_registro': uuid.uuid4().hex[:8], # ID temporal para el frontend
                                'hora': hora_texto,
                                'tipo': tipo_evento,
                                'estado': 'Por Validar', # Estado por defecto al leer el parquet
                                'metodo': metodo_ingreso
                            }

                            # Guardamos la marca en la lista de ese día
                            calendario_mes[fecha_texto]['marcaciones'].append(marca_individual)


                    # --- EVALUAR REGLAS (Día por día) ---
                    for fecha_txt, info_dia in calendario_mes.items():
                        
                        # Filtramos para no contar marcas descartadas
                        lista_marcas_activas = [m for m in info_dia['marcaciones'] if m['estado'] != 'Descartado']
                        total_marcas = len(lista_marcas_activas)
                        
                        # REGLA: 4 o 6 marcas activas Y SIN DUPLICADOS = "Por Validar". 
                        # Cualquier otra cosa (número distinto o tipos repetidos) = "Inconsistente".
                        if total_marcas > 0:
                            # Detectar si hay duplicados
                            tipos_activos = [m['tipo'] for m in lista_marcas_activas]
                            tiene_duplicados = len(tipos_activos) != len(set(tipos_activos))

                            # REGLA: 4 o 6 marcas Y SIN DUPLICADOS = Por Validar
                            if (total_marcas == 4 or total_marcas == 6) and not tiene_duplicados:
                                info_dia['estados_dia'].add('Por Validar')
                            else:
                                info_dia['estados_dia'].add('Inconsistente')
                        
                        # Convertimos el Set() a List() para que JSON/HTML lo entienda sin errores
                        info_dia['estados_dia'] = list(info_dia['estados_dia'])                        
                        # Almacenamos solo la lista de marcaciones en el diccionario para Alpine.js
                        marcas_json[fecha_txt] = info_dia['marcaciones']


                    # --- PASO 7: Agrupar Días por Semanas ---
                    semanas_agrupadas = {}
                    
                    # Detectamos en qué día de la semana cayó el 1er día del mes (0=Lunes, 6=Domingo)
                    desplazamiento_mes = datetime(int(anio), int(mes), 1).weekday()
                    
                    # Ordenamos cronológicamente los días que creamos en el Paso 6
                    for fecha_ordenada in sorted(calendario_mes.keys()):
                        dia_actual = calendario_mes[fecha_ordenada]
                        numero_dia_mes = dia_actual['fecha_obj'].day
                        
                        # Fórmula matemática para calcular en qué semana relativa cae este día
                        numero_semana = (numero_dia_mes + desplazamiento_mes - 1) // 7 + 1
                        
                        # Si la semana no existe en nuestro diccionario, la creamos
                        if numero_semana not in semanas_agrupadas:
                            semanas_agrupadas[numero_semana] = {
                                'nombre': f"Semana {numero_semana}", 
                                'dias': []
                            }
                            
                        # Agregamos el día a la lista de su semana correspondiente
                        semanas_agrupadas[numero_semana]['dias'].append(dia_actual)

                    # Aplanamos el diccionario en una lista de semanas ordenadas para el HTML
                    semanas_finales = [semanas_agrupadas[num] for num in sorted(semanas_agrupadas.keys())]

        except Exception as e:
            logger.error(f"Error procesando el parquet: {e}")
            flash("Ocurrió un error interno al leer los datos.", "error")

    # --- PASO 8: Renderizar Pantalla ---
    # Igualamos nuestras variables limpias a los nombres originales que espera el HTML
    return render_template(
        'users/user_mark_day_records.html',
        busqueda=empleado_req,       # Para que el select mantenga el nombre elegido
        mes_seleccionado=mes_req,    # Para que Flatpickr muestre el mes actual
        usuario=datos_usuario,       # Para la tarjeta de perfil
        semanas=semanas_finales,     # Para las tablas desplegables
        datos_js=marcas_json,         # Para que funcione el modal de edición
        anios_disponibles=lista_anios,   # <-- La lista de años desplegable
        meses_disponibles=lista_meses    # <-- La lista de meses desplegable
    )