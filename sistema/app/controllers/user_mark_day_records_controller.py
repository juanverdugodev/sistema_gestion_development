from flask import render_template, request, session, redirect, url_for, flash, jsonify
from utils.file_manager import get_uploads_storage_parquet
from datetime import datetime
import logging
import os
import pandas as pd
import uuid
import re
import numpy as np

# --- REEMPLAZO: Instanciamos los dos canales de logs ---
audit_logger = logging.getLogger('auditoria')
sys_logger = logging.getLogger('sistema')


# ESCANEO DE ARCHIVOS (MESES Y AÑOS DINÁMICOS) PARA EL CAMPO SELECT HTML

def obtener_filtros_disponibles():
    """Escanea la carpeta de parquets y devuelve listas de meses y años existentes."""
    folder = get_uploads_storage_parquet()
    anios = set()
    meses_num = set()
    
    if os.path.exists(folder):
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            # Verificamos que sea una carpeta y que su nombre coincida con MM-YYYY
            if os.path.isdir(item_path):
                match = re.match(r"(\d{2})-(\d{4})", item)
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
        nombre_carpeta_y_archivo = f"{mes}-{anio}"
        ruta_archivo = os.path.join(get_uploads_storage_parquet(), nombre_carpeta_y_archivo, f"{nombre_carpeta_y_archivo}.parquet")

        if not os.path.exists(ruta_archivo):
            return jsonify({"exists": False, "names": []}), 200

        df = pd.read_parquet(ruta_archivo)
        nombres_unicos = df['nombre'].dropna().unique().tolist()
        
        # Responde con un JSON: {"exists": true, "names": ["Admin Admin", "Juan..."]}
        return jsonify({"exists": True, "names": sorted(nombres_unicos)}), 200
        
    except Exception as e:
        sys_logger.error(f"Error al obtener nombres: {e}")
        return jsonify({"exists": False, "names": [], "error": str(e)}), 500



# FUNCIÓN PRINCIPAL: CONSULTA DE MARCACIONES .parquet

def validar_marcaciones():
    """Dibuja la pantalla y procesa las marcaciones si se envían filtros."""
    
    # Capturar mensaje de éxito tras recargar
    if request.args.get('success') == 'true':
        flash("Las marcaciones han sido actualizadas y validadas correctamente en el registro.", "success")

    # --- PASO 1: Seguridad y Captura de Parámetros ---
    if session.get('rol') != 'Administrador':
        flash("Acceso denegado.", "error")
        return redirect(url_for('main.home'))

    empleado_req = request.args.get('busqueda', '').strip() 
    mes_req = request.args.get('mes', '')               
    admin_actual = session.get('username', 'Usuario Desconocido')

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
            nombre_carpeta_y_archivo = f"{mes}-{anio}"
            ruta_archivo = os.path.join(get_uploads_storage_parquet(), nombre_carpeta_y_archivo, f"{nombre_carpeta_y_archivo}.parquet")

            if not os.path.exists(ruta_archivo):
                flash(f"No existen registros para {mes}-{anio}.", "error")
            else:
                df_total = pd.read_parquet(ruta_archivo)

                # --- PASO 4: Filtrar datos del empleado ---
                df_emp = df_total[df_total['nombre'] == empleado_req].copy()

                if df_emp.empty:
                    flash(f"No hay registros de {empleado_req} en este mes.", "warning")

                else:
                    # LOG DE AUDITORÍA: El usuario consultó un registro específico
                    audit_logger.info(f"El usuario '{admin_actual}' consulto el registro de asistencia de '{empleado_req}' correspondiente al mes {mes_req}.")

                    # Ordenar fechas cronológicamente
                    df_emp['fecha_hora'] = pd.to_datetime(df_emp['fecha_hora'])
                    df_emp = df_emp.sort_values(by=['fecha', 'hora'])

                    # --- PASO 5: Extraer Perfil del Usuario ---
                    info_base = df_emp.iloc[0]

                    # --- NUEVO: Limpieza visual de la Cédula (Solo para el Front) ---
                    # Pandas convierte "01984573" a "1984573.0". Vamos a revertir eso estéticamente.
                    cedula_raw = str(info_base.get('cedula', 'N/A')).strip()

                    # 1. Le quitamos el ".0" del final si lo tiene
                    if cedula_raw.endswith('.0'):
                        cedula_raw = cedula_raw[:-2]
                        
                    # 2. Si lo que queda es un número, lo rellenamos con cero a la izquierda hasta 10 dígitos
                    if cedula_raw.isdigit():
                        cedula_visual = cedula_raw.zfill(10)
                    else:
                        cedula_visual = cedula_raw # Si dice 'nan' o 'N/A', lo dejamos intacto
                    # -----------------------------------------------------------------

                    # Leer el archivo de resumen para sacar entrada/salida oficial
                    archivo_resumen = f"resumen-{mes}-{anio}.parquet"
                    ruta_resumen = os.path.join(get_uploads_storage_parquet(), nombre_carpeta_y_archivo, archivo_resumen)

                    entrada_oficial_str = ''
                    salida_oficial_str = ''
                    receso_oficial_str = ''
                    grafica_base64 = ''

                    if os.path.exists(ruta_resumen):
                        df_resumen = pd.read_parquet(ruta_resumen)
                        df_res_emp = df_resumen[df_resumen['funcionario'] == empleado_req]
                        if not df_res_emp.empty:
                            info_res = df_res_emp.iloc[0]

                            es_horario_oficial = False

                            # --- LÓGICA DE PRIORIDAD PARA ENTRADA ---
                            val_ent_oficial = info_res.get('entradaOficial')
                            val_tend_ent = info_res.get('tendEntrada')

                            if pd.notna(val_ent_oficial) and str(val_ent_oficial).strip() and str(val_ent_oficial).strip() not in ('nan', 'None', ''):
                                entrada_oficial_str = str(val_ent_oficial).strip()[:5]  # <-- [:5] Corta a HH:MM para el front
                                es_horario_oficial = True
                            elif pd.notna(val_tend_ent) and str(val_tend_ent).strip() and str(val_tend_ent).strip() not in ('nan', 'None', ''):
                                entrada_oficial_str = str(val_tend_ent).strip()[:5]     # <-- [:5] Corta a HH:MM para el front

                            # --- LÓGICA DE PRIORIDAD PARA SALIDA ---
                            val_sal_oficial = info_res.get('salidaOficial')
                            val_tend_sal = info_res.get('tendSalida')

                            if pd.notna(val_sal_oficial) and str(val_sal_oficial).strip() and str(val_sal_oficial).strip() not in ('nan', 'None', ''):
                                salida_oficial_str = str(val_sal_oficial).strip()[:5]   # <-- [:5] Corta a HH:MM para el front
                                es_horario_oficial = True
                            elif pd.notna(val_tend_sal) and str(val_tend_sal).strip() and str(val_tend_sal).strip() not in ('nan', 'None', ''):
                                salida_oficial_str = str(val_tend_sal).strip()[:5]      # <-- [:5] Corta a HH:MM para el front

                            # --- NUEVA LÓGICA DE PRIORIDAD PARA RECESO ---
                            val_rec_oficial = info_res.get('recesoOficial')
                            val_tend_sal_al = info_res.get('tendSalidaAl')
                            val_tend_ent_al = info_res.get('tendEntradaAl')

                            # 1. Si existe un receso oficial ya guardado
                            if pd.notna(val_rec_oficial) and str(val_rec_oficial).strip() and str(val_rec_oficial).strip() not in ('nan', 'None', ''):
                                receso_oficial_str = str(val_rec_oficial).strip()[:5]   # <-- [:5] Corta a HH:MM para el front
                                es_horario_oficial = True
                            
                            # 2. Si no existe oficial, calculamos la diferencia del Clúster
                            elif pd.notna(val_tend_sal_al) and pd.notna(val_tend_ent_al):
                                t_sal = str(val_tend_sal_al).strip()
                                t_ent = str(val_tend_ent_al).strip()
                                if t_sal not in ('nan', 'None', '') and t_ent not in ('nan', 'None', ''):
                                    try:
                                        # Extraemos HH y MM (El slicing [:5] ya nos asegura no tomar segundos si los hubiera)
                                        h_sal, m_sal = int(t_sal[:2]), int(t_sal[3:5])
                                        h_ent, m_ent = int(t_ent[:2]), int(t_ent[3:5])
                                        
                                        minutos_sal = (h_sal * 60) + m_sal
                                        minutos_ent = (h_ent * 60) + m_ent
                                        
                                        diff = abs(minutos_ent - minutos_sal) # Calculamos tiempo transcurrido
                                        h_diff = diff // 60
                                        m_diff = diff % 60
                                        
                                        # Aquí ya nace formateado sin segundos, así que lo dejamos tal cual
                                        receso_oficial_str = f"{h_diff:02d}:{m_diff:02d}"
                                    except Exception as e:
                                        sys_logger.error(f"Error calculando tiempo de receso: {e}")


                            # --- Extraer la gráfica generada por Matplotlib ---
                            if 'grafica' in info_res and pd.notna(info_res['grafica']):
                                grafica_base64 = str(info_res['grafica'])

                    # Se envía al front
                    datos_usuario = {
                        'nombres': empleado_req,
                        'cedula': cedula_visual,
                        'departamento': str(info_base.get('departamento', 'N/A')),
                        'entrada_oficial': entrada_oficial_str,
                        'salida_oficial': salida_oficial_str,
                        'receso_oficial': receso_oficial_str,
                        'es_oficial': es_horario_oficial,    
                        'grafica': grafica_base64
                    }

                    # Contamos el total de registros y los días únicos
                    total_registros = len(df_emp)
                    total_dias = df_emp['fecha_hora'].dt.date.nunique()

                    flash(f"Se encontraron {total_dias} días con {total_registros} registros para el funcionario {empleado_req}.")

                    # --- PASO 6: Agrupar por Días ---
                    nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    
                    # Diccionario donde agruparemos las marcas. Llave = '2026-03-05', Valor = Diccionario con info del día
                    calendario_mes = {}

                    # Iteramos sobre cada fila del DataFrame del empleado (SIN MODIFICAR EL DF)
                    for _, fila_marca in df_emp.iterrows():
                        if pd.notna(fila_marca['fecha_hora']):
                            
                            # --- MODIFICACIÓN: Extracción de hora para visualización y ancla exacta ---
                            fecha_limpia = fila_marca['fecha_hora'].date()          # Ej: datetime.date(2026, 3, 5)
                            fecha_texto = fecha_limpia.strftime('%Y-%m-%d')         # Ej: '2026-03-05'

                            # --- CORRECCIÓN: LEER LA COLUMNA EDITABLE 'hora' ---
                            # Tomamos la hora de la columna que SÍ se actualiza
                            hora_obj = fila_marca['hora']

                            # Prevenimos errores de tipo de dato (si Pandas devuelve un objeto time o un string)
                            if hasattr(hora_obj, 'strftime'):
                                hora_texto = hora_obj.strftime('%H:%M')     # Ej: '18:00' (Lo que ve el usuario)
                                hora_exacta = hora_obj.strftime('%H:%M:%S') # Ej: '18:00:00' (Ancla de búsqueda)
                            else:
                                hora_texto = str(hora_obj)[:5]              # Ej: '18:00'
                                hora_exacta = str(hora_obj)[:8]             # Ej: '18:00:00'

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

                            # --- CONDICIONAL DE JERARQUÍA DE MARCAS ---
                            m_real = fila_marca.get('marcacionReal')
                            m_cluster = fila_marca.get('marcacionCluster')

                            # 1. Si existe corrección humana en marcacionReal, tiene prioridad.
                            if pd.notna(m_real) and str(m_real).strip() and str(m_real).strip() != 'nan':
                                tipo_evento = str(m_real).strip()
                            # 2. Si no, usamos el cálculo de la máquina del cluster.
                            elif pd.notna(m_cluster) and str(m_cluster).strip() and str(m_cluster).strip() != 'nan':
                                tipo_evento = str(m_cluster).strip()
                            # 3. Si todo falla, usamos el dato crudo sin cluster.
                            else:
                                tipo_evento = fila_marca.get('tipoMarcacion', 'Registro')

                            # Guardamos el cluster original intacto para no perderlo al guardar
                            cluster_puro = m_cluster if pd.notna(m_cluster) else np.nan

                            # --- LECTURA DE VALIDACIÓN ---
                            estado_guardado = fila_marca.get('tipoValidacion')
                            if pd.isna(estado_guardado) or not str(estado_guardado).strip() or str(estado_guardado).strip() == 'nan':
                                estado_final = 'Por Validar'
                            else:
                                estado_final = str(estado_guardado).strip()

                            # Construimos el diccionario de la marca individual

                            # --- MODIFICACIÓN: Inclusión de ancla temporal exacta ---
                            marca_individual = {
                                'id_registro': uuid.uuid4().hex[:8],
                                'hora': hora_texto,
                                'hora_original': hora_exacta, # Se preservan los segundos para búsqueda
                                'tipo': tipo_evento,    
                                'estado': estado_final, 
                                'metodo': metodo_ingreso,
                                'cluster_original': cluster_puro 
                            }
                            # -------------------------------------------------------

                            # Guardamos la marca en la lista de ese día
                            calendario_mes[fecha_texto]['marcaciones'].append(marca_individual)


                    # --- EVALUAR REGLAS (Día por día) ---
                    for fecha_txt, info_dia in calendario_mes.items():
                        
                        # Filtramos para no contar marcas descartadas
                        lista_marcas_activas = [m for m in info_dia['marcaciones'] if m['estado'] != 'Descartado']
                        total_marcas = len(lista_marcas_activas)
                        
                        # REGLA: módulo de 2, marcas activas Y SIN DUPLICADOS = "Por Validar". 
                        # Cualquier otra cosa (número distinto o tipos repetidos) = "Inconsistente".
                        if total_marcas > 0:
                            # Detectar si hay duplicados
                            tipos_activos = [m['tipo'] for m in lista_marcas_activas]
                            tiene_duplicados = len(tipos_activos) != len(set(tipos_activos))

                            # REGLA: Cantidad par de marcas (módulo 2 == 0) Y SIN DUPLICADOS = Por Validar
                            if (total_marcas % 2 == 0) and not tiene_duplicados:
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
            sys_logger.error(f"Error procesando el parquet: {e}")
            flash("Ocurrió un error interno al leer los datos.", "error")

    # --- PASO 8: Renderizar Pantalla ---
    # Igualamos nuestras variables limpias a los nombres originales que espera el HTML
    return render_template(
        'users/audit/user_mark_day_records.html',
        busqueda=empleado_req,       # Para que el select mantenga el nombre elegido
        mes_seleccionado=mes_req,    # Para que Flatpickr muestre el mes actual
        usuario=datos_usuario,       # Para la tarjeta de perfil
        semanas=semanas_finales,     # Para las tablas desplegables
        datos_js=marcas_json,        # Para que funcione el modal de edición
        anios_disponibles=lista_anios,   # <-- La lista de años desplegable
        meses_disponibles=lista_meses    # <-- La lista de meses desplegable
    )

def guardar_edicion_jornada_api():
    """Recibe las ediciones del frontend y actualiza el archivo .parquet modificando SOLO las columnas permitidas."""
    if session.get('rol') != 'Administrador':
        return jsonify({"success": False, "error": "Acceso denegado"}), 403

    datos = request.get_json()
    nombre_funcionario = datos.get('id_funcionario')
    mes_completo = datos.get('mes_completo')
    # Usamos {} por defecto en caso de que no venga nada
    fechas_modificadas = datos.get('fechas_modificadas', {})
    
    admin_actual = session.get('username', 'Usuario Desconocido')

    # Capturar las penalizaciones por día
    penalizaciones_diarias = datos.get('penalizaciones_diarias', {})

    # Las fechas_modificadas pueden estar vacías si solo se editó el Horario (Entrada/Salida/Receso)
    if not nombre_funcionario or not mes_completo:
        return jsonify({"success": False, "error": "Datos incompletos: Falta funcionario o mes."}), 400

    try:
        # 1. Localizar el archivo parquet correcto
        anio, mes = mes_completo.split('-')
        nombre_carpeta = f"{mes}-{anio}"
        ruta_archivo = os.path.join(get_uploads_storage_parquet(), nombre_carpeta, f"{nombre_carpeta}.parquet")

        if not os.path.exists(ruta_archivo):
            return jsonify({"success": False, "error": "El archivo de este mes ya no existe."}), 404

        # 2. Leer el DataFrame original
        df = pd.read_parquet(ruta_archivo)

        # 3. Extraer la data base del empleado (departamento, cédula, etc.) para las inserciones manuales
        df_empleado = df[df['nombre'] == nombre_funcionario]
        if df_empleado.empty:
            return jsonify({"success": False, "error": "El empleado no existe en el archivo."}), 404

        # Extraemos un registro "modelo" por si el admin creó una marca nueva manual
        fila_modelo = df_empleado.iloc[0].copy()
        
        nuevas_filas_manuales = []

        # 4. Procesar cada día modificado
        for fecha_str, marcas_js in fechas_modificadas.items():
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
            for m in marcas_js:
                hora_actual = m['hora']
                hora_original = m.get('hora_original') # Si es un registro nuevo desde el modal, será None
                estado = m['estado']
                tipo_real = m['tipo']

                # --- CASO A: ES UN REGISTRO NUEVO CREADO MANUALMENTE EN EL FRONTEND ---
                if not hora_original:
                    nueva_fila = fila_modelo.copy()
                    
                    # Como es un registro inventado, SÍ definimos fecha_hora, fecha y hora
                    fecha_hora_obj = pd.to_datetime(f"{fecha_str} {hora_actual}:00")
                    nueva_fila['fecha_hora'] = fecha_hora_obj
                    nueva_fila['tipoMarcacion'] = np.nan     # Nulo porque no se generó en método físico
                    nueva_fila['verificacion'] = m['metodo'] # 'MANUAL desde el JSON'
                    nueva_fila['fecha'] = fecha_obj
                    nueva_fila['hora'] = fecha_hora_obj.time()

                    nueva_fila['marcacionCluster'] = np.nan # Nulo porque la máquina nunca lo calculó
                    nueva_fila['marcacionReal'] = tipo_real # SÍ lleva el dato porque es una inserción humana
                    nueva_fila['tipoValidacion'] = estado
                    
                    nuevas_filas_manuales.append(nueva_fila.to_dict())
                
                # --- MODIFICACIÓN: Lógica de actualización in-place con precisión de segundos ---
                else:
                    # Buscamos la fila exacta usando la hora_original (con sus segundos) como ancla
                    hora_orig_obj = pd.to_datetime(f"{fecha_str} {hora_original}").time()
                    mask_exacta = (df['nombre'] == nombre_funcionario) & (df['fecha'] == fecha_obj) & (df['hora'] == hora_orig_obj)
                    
                    if df[mask_exacta].shape[0] > 0:
                        # 1. Si la hora fue modificada en el frontend (Comparación de HH:MM)
                        if hora_actual != hora_original[:5]:
                            nueva_hora_obj = pd.to_datetime(f"{fecha_str} {hora_actual}:00").time()
                            # Actualización de la columna hora
                            df.loc[mask_exacta, 'hora'] = nueva_hora_obj
                        
                        # 2. Actualización de metadatos de revisión
                        df.loc[mask_exacta, 'marcacionReal'] = tipo_real
                        df.loc[mask_exacta, 'tipoValidacion'] = estado
                # --------------------------------------------------------------------------------

        # 5. Inyectar las nuevas filas manuales (si las hubo)
        if nuevas_filas_manuales:
            df_nuevas = pd.DataFrame(nuevas_filas_manuales)
            
            # Aseguramos compatibilidad de tipos con pyarrow
            df_nuevas['marcacionCluster'] = df_nuevas['marcacionCluster'].astype('object')
            df_nuevas['marcacionReal'] = df_nuevas['marcacionReal'].astype('object')
            df_nuevas['tipoValidacion'] = df_nuevas['tipoValidacion'].astype('object')

            # Aseguramos también la columna tipoMarcacion por los nulos
            df_nuevas['tipoMarcacion'] = df_nuevas['tipoMarcacion'].astype('object')
            
            df = pd.concat([df, df_nuevas], ignore_index=True)

        # 6. Ordenar el DataFrame general para mantener la coherencia cronológica
        df = df.sort_values(by=['nombre', 'fecha_hora']).reset_index(drop=True)

        # 7. Sobrescribir el Parquet Original de manera segura
        df.to_parquet(ruta_archivo, engine='pyarrow', compression='snappy')

        # --- ACTUALIZAR EL PARQUET DE RESUMEN (Horarios Oficiales) ---
        entrada_oficial_editada = datos.get('entrada_oficial')
        salida_oficial_editada = datos.get('salida_oficial')
        receso_oficial_editado = datos.get('receso_oficial')
        atraso_total_calculado = datos.get('atraso_total')
        
        archivo_resumen = f"resumen-{mes}-{anio}.parquet"
        ruta_resumen = os.path.join(get_uploads_storage_parquet(), nombre_carpeta, archivo_resumen)
        
        if os.path.exists(ruta_resumen) and (entrada_oficial_editada or salida_oficial_editada):
            df_resumen = pd.read_parquet(ruta_resumen)
            mask_resumen = df_resumen['funcionario'] == nombre_funcionario
            
            if mask_resumen.any():


                # Forzamos explícitamente a que las columnas de tiempo sean tipo 'object' (texto)
                columnas_tiempo = ['entradaOficial', 'salidaOficial', 'recesoOficial', 'atrasoTotal']
                for col in columnas_tiempo:
                    if col in df_resumen.columns:
                        df_resumen[col] = df_resumen[col].astype('object')
                # ------------------------------------------------

                if entrada_oficial_editada:
                    df_resumen.loc[mask_resumen, 'entradaOficial'] = entrada_oficial_editada
                if salida_oficial_editada:
                    df_resumen.loc[mask_resumen, 'salidaOficial'] = salida_oficial_editada
                if receso_oficial_editado:
                    df_resumen.loc[mask_resumen, 'recesoOficial'] = receso_oficial_editado
                # Guardamos la métrica global de atraso (ej: '01:20')
                if atraso_total_calculado:
                    df_resumen.loc[mask_resumen, 'atrasoTotal'] = atraso_total_calculado
                
                # Guardamos el segundo parquet
                df_resumen.to_parquet(ruta_resumen, engine='pyarrow', compression='snappy')

        # --- ACTUALIZAR EL PARQUET DIARIO (Parquet 3) ---
        penalizaciones_diarias = datos.get('penalizaciones_diarias', {})
        
        if penalizaciones_diarias or fechas_modificadas:
            archivo_diario = f"diario-{mes}-{anio}.parquet"
            ruta_diario = os.path.join(get_uploads_storage_parquet(), nombre_carpeta, archivo_diario)
            
            if os.path.exists(ruta_diario):
                df_diario = pd.read_parquet(ruta_diario)
                
                # Forzamos tipo object para evitar el error float64 en el Parquet 3
                columnas_penalizaciones = ['atrasoEntrada', 'atrasoAlmuerzo', 'atrasoSalida']
                for col in columnas_penalizaciones:
                    if col not in df_diario.columns:
                        df_diario[col] = None # Las creamos si por algún motivo no existían
                    df_diario[col] = df_diario[col].astype('object')

                # --- Inyectar numMarcacionesFinal ---
                
                for fecha_str, marcas_js in fechas_modificadas.items():
                    mask_diario = (df_diario['funcionario'] == nombre_funcionario) & (df_diario['fecha'].astype(str).str.startswith(fecha_str))
                    
                    if mask_diario.any():
                        # Guardamos el tamaño del arreglo que nos envía JS
                        df_diario.loc[mask_diario, 'numMarcacionesFinal'] = len(marcas_js)

                # Iteramos día por día para guardar sus penalizaciones
                for fecha_str, penalizaciones in penalizaciones_diarias.items():
                    
                    mask_diario = (df_diario['funcionario'] == nombre_funcionario) & (df_diario['fecha'].astype(str).str.startswith(fecha_str))
                    
                    if mask_diario.any():
                        # Si JS nos manda un atraso lo pone, si no, por defecto pone "00:00"
                        df_diario.loc[mask_diario, 'atrasoEntrada'] = penalizaciones.get('atrasoEntrada', '00:00')
                        df_diario.loc[mask_diario, 'atrasoAlmuerzo'] = penalizaciones.get('atrasoAlmuerzo', '00:00')
                        df_diario.loc[mask_diario, 'atrasoSalida'] = penalizaciones.get('atrasoSalida', '00:00')
                
                # Guardamos el tercer parquet sobrescribiéndolo de forma segura
                df_diario.to_parquet(ruta_diario, engine='pyarrow', compression='snappy')

        # LOG DE AUDITORÍA: El Administrador guardó cambios exitosamente
        audit_logger.info(f"El usuario '{admin_actual}' modifico y audito las marcaciones de '{nombre_funcionario}' correspondientes al mes {mes_completo}.")

        return jsonify({"success": True}), 200

    except Exception as e:
        sys_logger.error(f"Error al sobrescribir parquet in-place: {e}")
        return jsonify({"success": False, "error": str(e)}), 500