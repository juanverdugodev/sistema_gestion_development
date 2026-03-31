# utils/register_engine.py

import pandas as pd
import numpy as np
import logging
import matplotlib
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from io import BytesIO
import base64

# FUNDAMENTAL PARA FLASK: Evita que Matplotlib intente abrir ventanas gráficas y crashee el servidor
matplotlib.use('Agg')

# --- REEMPLAZO: Instanciamos el canal de logs de sistema ---
sys_logger = logging.getLogger('sistema')

def asignar_marcacion(hora):
    """Celda 14 """
    limEntrada = 12
    if hora < limEntrada:  
        return 'Entrada'
    else:
        return 'Salida'

def etiquetar_clusters(numClusters, centroides):
    """Celda 14 """
    df_cluster = pd.DataFrame(centroides, columns=['centroide'])
    df_cluster_ordenado = df_cluster.sort_values(by='centroide')

    if numClusters >= 2:
        min_centroide = df_cluster_ordenado['centroide'].min()
        df_cluster_ordenado.loc[df_cluster_ordenado['centroide'] == min_centroide, 'marcacion'] = 'Entrada'
        
        max_centroide = df_cluster_ordenado['centroide'].max()
        df_cluster_ordenado.loc[df_cluster_ordenado['centroide'] == max_centroide, 'marcacion'] = 'Salida'

        df_vacios = df_cluster_ordenado[df_cluster_ordenado['marcacion'].isna()]

        if len(df_vacios) >= 2:
            min_centroide_central = df_vacios['centroide'].min()
            max_centroide_central = df_vacios['centroide'].max()
            df_cluster_ordenado.loc[df_cluster_ordenado['centroide'] == min_centroide_central, 'marcacion'] = 'Salida Almuerzo'
            df_cluster_ordenado.loc[df_cluster_ordenado['centroide'] == max_centroide_central, 'marcacion'] = 'Regreso Almuerzo'
            df_cluster_ordenado['marcacion'] = df_cluster_ordenado['marcacion'].replace(np.nan, 'Desconocido') 
        else:
            df_cluster_ordenado['marcacion'] = df_cluster_ordenado['marcacion'].replace(np.nan, 'Desconocido') 
    else: 
        df_cluster_ordenado['marcacion'] = df_cluster_ordenado['centroide'].apply(asignar_marcacion)

    return df_cluster_ordenado

def convertir_hora_decimal(hora_decimal):
    """Convierte la hora en formato decimal de vuelta a formato de texto HH:MM:SS"""
    horas = int(hora_decimal)
    minutos_totales = (hora_decimal - horas) * 60
    minutos = int(minutos_totales)
    segundos = round((minutos_totales - minutos) * 60)

    if segundos == 60:
        minutos += 1
        segundos = 0
        if minutos == 60:
            horas += 1
            minutos = 0

    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def clusterizar(df):
    """
    Agrupa toda la lógica del cuaderno (Celdas 2 a la 16).
    Recibe el DataFrame crudo leído del Excel y devuelve el DataFrame procesado.
    """
    
    sys_logger.info("Iniciando motor de Machine Learning (K-Means) para el procesamiento de marcaciones...")

    # --- INICIO DE ESTRUCTURACIÓN DE CABECERAS PARA LOS 3 PARQUETS ---

    # 1. ESTRUCTURACIÓN DEL PARQUET PRINCIPAL (df)
    # Celda 2: Renombrar (Ajusta los nombres de las columnas leídas del Excel)
    df = df.rename(columns={
        'Dpto.': 'departamento',
        'Nombre': 'nombre',
        'AC_No': 'numAcceso',
        'Fecha/Hora': 'fecha_hora',
        'Marc-Ent/Sal':'tipoMarcacion',
        'Reloj ID':'relojID',
        'No. Cédula':'cedula',
        'Incidencia':'incidencia',
        'Verificación':'verificacion',
        'CardNo':'numTarjeta'
    })

    # Celda 3: Eliminar columnas (Borra cabeceras que no se usarán)
    df = df.drop(columns=['relojID', 'incidencia', 'numTarjeta'], errors='ignore')

    # Celda 5: Homogeneizar
    if 'verificacion' in df.columns:
        df['verificacion'] = df['verificacion'].str.upper()

    # Celda 6: Fechas (Crea las nuevas columnas 'fecha' y 'hora' extrayéndolas de 'fecha_hora')
    df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], format='%d/%m/%Y %H:%M:%S')
    df['fecha'] = df['fecha_hora'].dt.date
    df['hora'] = df['fecha_hora'].dt.time

    unique_names = df['nombre'].dropna().unique().tolist()
    
    sys_logger.info(f"Se detectaron {len(unique_names)} funcionarios unicos para analisis.")

    # 2. CREACIÓN DESDE CERO DEL PARQUET DE RESUMEN MENSUAL (df_resumen)
    # Celda 8: Estructura resumen
    columnasResumen = ['funcionario','diasAsistidos','tendEntrada','tendSalidaAl','tendEntradaAl','tendSalida','entradaOficial','salidaOficial','atrasoTotal', 'grafica']
    df_resumen = pd.DataFrame(columns=columnasResumen)
    df_resumen['funcionario'] = df_resumen['funcionario'].astype(str)
    # Se omiten temporalmente los astype y to_timedelta de columnas vacías para evitar errores de pandas con datos sin inicializar
    
    # 3. CREACIÓN DESDE CERO DEL PARQUET DIARIO (df_diario)
    # Celda 9: Estructura diario
    columnasDiario = ['funcionario','fecha','numMarcacionesInicial','numMarcacionesFinal','atrasoEntrada','atrasoAlmuerzo','atrasoSalida']
    df_diario = pd.DataFrame(columns=columnasDiario)

    # --- FIN DE ESTRUCTURACIÓN INICIAL DE CABECERAS ---

    # Celda 10: Generando data resumen
    filas_resumen = []
    for nombre_filtrado in unique_names:
        dias = len(df.loc[(df['nombre'] == nombre_filtrado)]['fecha'].unique())
        filas_resumen.append({'funcionario': str(nombre_filtrado), 'diasAsistidos': dias})
    df_resumen = pd.concat([df_resumen, pd.DataFrame(filas_resumen)], ignore_index=True)

    # Segunda Celda 9: Generando data diario
    filas_diario = []
    for nombre_filtrado in unique_names:
        fechas_unicas = df.loc[(df['nombre'] == nombre_filtrado)]['fecha'].unique()
        for fecha_filtrada in fechas_unicas:
            registro_temp = df.loc[(df['nombre'] == nombre_filtrado) & (df['fecha'] == fecha_filtrada)]
            cant_registros = len(registro_temp['hora'].values)
            filas_diario.append({
                'funcionario': str(nombre_filtrado),
                'fecha': fecha_filtrada,
                'numMarcacionesInicial': cant_registros
            })
    df_diario = pd.concat([df_diario, pd.DataFrame(filas_diario)], ignore_index=True)


    # añadir la columna vacía al DF principal
    # forzamos el tipo 'object' para que acepte texto sin que PyArrow falle
    df['marcacionCluster'] = np.nan
    df['marcacionCluster'] = df['marcacionCluster'].astype('object')

    # Guarda la corrección manual del administrador (Nace nula)
    df['marcacionReal'] = np.nan
    df['marcacionReal'] = df['marcacionReal'].astype('object')

    # Inicializa todos los registros como nulos (NaN) para que en el futuro 
    # se sobreescriban con 'Válido' o 'Actualizado'.
    df['tipoValidacion'] = np.nan
    df['tipoValidacion'] = df['tipoValidacion'].astype('object')

    # --- FIN DE INYECCIÓN DE CABECERAS FINALES ---
    entradas = np.arange(7, 9.5, 0.5)
    salidas = np.arange(16,20,0.5)

    
    # Celda 16: El bucle principal de KMeans y Gráficas
    for nombre_filtrado in unique_names:
        columnas_a_seleccionar = ['fecha', 'hora']
        df_f = df[df['nombre'] == nombre_filtrado][columnas_a_seleccionar].copy()
        
        if df_f.empty:
            sys_logger.warning(f"Algoritmo omitio a '{nombre_filtrado}': No existen datos procesables.")
            continue
            
        df_f['fecha'] = pd.to_datetime(df_f['fecha'])
        df_f['hora'] = pd.to_datetime(df_f['hora'], format='%H:%M:%S')

        df_f['hora_decimal'] = (
            df_f['hora'].dt.hour +
            df_f['hora'].dt.minute/60 +
            df_f['hora'].dt.second/3600
        )

        # Aplicar K-means
        # Se asegura de no extraer max() de una serie vacía
        moda_serie = df_diario.loc[df_diario['funcionario'] == str(nombre_filtrado), 'numMarcacionesInicial'].mode()
        if not moda_serie.empty:
            n_clusters = int(moda_serie.max())
        else:
            n_clusters = 1 # Valor por defecto si no hay moda

        # Protección en caso de que los datos sean menores a los clusters
        n_clusters = min(n_clusters, len(df_f))
        if n_clusters == 0:
            sys_logger.warning(f"Algoritmo omitio a '{nombre_filtrado}': 0 clusters detectados para agrupar.")
            continue

        kmeans = KMeans(n_clusters=n_clusters, random_state=0)
        df_f['cluster'] = kmeans.fit_predict(df_f[['hora_decimal']])

        # Gráfica
        plt.figure(figsize=(10, 6))
        colors = plt.get_cmap('viridis')

        for cluster in range(n_clusters):
            cluster_data = df_f[df_f['cluster'] == cluster]
            plt.scatter(cluster_data['fecha'], cluster_data['hora_decimal'],
                        color=colors(cluster / max(1, n_clusters - 1)), label=f'Cluster {cluster + 1}')

        centroids = kmeans.cluster_centers_

        for centroid in centroids:
            plt.axhline(y=centroid[0], color='red', linestyle='--', linewidth=1)

        plt.xlabel("Fecha")
        plt.ylabel("Hora del día (decimal)")
        plt.title(f"Marcaciones de Horas - {nombre_filtrado}")
        plt.xticks(rotation=45)
        plt.ylim(0, 24)
        plt.grid()
        plt.legend()

        # Guardar a base64
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close() # Cerrar la figura para liberar RAM del servidor

        df_resumen.loc[df_resumen['funcionario'] == str(nombre_filtrado), 'grafica'] = image_base64
        df_etiquetado = etiquetar_clusters(n_clusters, centroids)

        # Extracción de centroides (tendencias) solo si existen para evitar errores y dejar los NaN correspondientes
        
        # Entrada
        val_entrada = df_etiquetado.loc[df_etiquetado['marcacion'] == 'Entrada', 'centroide'].values
        if len(val_entrada) > 0:
            df_resumen.loc[df_resumen['funcionario'] == str(nombre_filtrado), 'tendEntrada'] = convertir_hora_decimal(val_entrada[0])            
            entrada_cercana = entradas[np.abs(entradas - val_entrada[0]).argmin()]
        else:
            entrada_cercana = 8
            
        # Salida Almuerzo
        val_salida_almuerzo = df_etiquetado.loc[df_etiquetado['marcacion'] == 'Salida Almuerzo', 'centroide'].values
        if len(val_salida_almuerzo) > 0:
            df_resumen.loc[df_resumen['funcionario'] == str(nombre_filtrado), 'tendSalidaAl'] = convertir_hora_decimal(val_salida_almuerzo[0])
            
        # Regreso Almuerzo
        val_regreso_almuerzo = df_etiquetado.loc[df_etiquetado['marcacion'] == 'Regreso Almuerzo', 'centroide'].values
        if len(val_regreso_almuerzo) > 0:
            df_resumen.loc[df_resumen['funcionario'] == str(nombre_filtrado), 'tendEntradaAl'] = convertir_hora_decimal(val_regreso_almuerzo[0])
            
        # Salida
        val_salida = df_etiquetado.loc[df_etiquetado['marcacion'] == 'Salida', 'centroide'].values
        if len(val_salida) > 0:
            df_resumen.loc[df_resumen['funcionario'] == str(nombre_filtrado), 'tendSalida'] = convertir_hora_decimal(val_salida[0])
            salida_cercana = salidas[np.abs(salidas - val_salida[0]).argmin()]
        else:
            salida_cercana = entrada_cercana + 9 # ( laborables + 1 de almuerzo)

        df_resumen.loc[df_resumen['funcionario'] == nombre_filtrado, 'entradaOficial'] = convertir_hora_decimal(entrada_cercana)
        df_resumen.loc[df_resumen['funcionario'] == nombre_filtrado, 'salidaOficial'] = convertir_hora_decimal(salida_cercana)

        df_f['cluster'] = df_f['cluster'].map(df_etiquetado['marcacion'])

        # Actualizar el DataFrame principal
        df.loc[df_f.index, 'marcacionCluster'] = df_f['cluster']

    sys_logger.info("Motor de Machine Learning finalizado exitosamente. Todas las graficas y DataFrames fueron generados.")

    # Para no perder el trabajo de resumen y diario, aunque el parquet principal es df, 
    # retornamos todo. El controlador decidirá qué guardar.
    return df, df_resumen, df_diario