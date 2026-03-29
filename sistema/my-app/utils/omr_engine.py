""" [EXPERIMENTAL] CONTROLADOR EXPERIMENTAL PARA ESCALABILIDAD """

import cv2
import numpy as np
from pdf2image import convert_from_path
from pyzbar.pyzbar import decode
import json
import logging

logging.basicConfig(level=logging.INFO)

class OMREngine:
    def __init__(self):
        # 1. COORDENADAS CALIBRADAS PARA LIENZO FIJO (1600x2200)        
        # Coordenadas de Firma
        self.coords_firma = (758, 1900, 804, 130)
        
        # Coordenadas de Horarios (x, y, w, h)
        self.bas_x, self.bas_w, self.bas_h = 160, 1388, 50
        self.secciones_horarios = [
            ("entrada_principal",   (self.bas_x, 410, self.bas_w, self.bas_h),  (self.bas_x, 508, self.bas_w, self.bas_h)),
            ("salida_intermedia",   (self.bas_x, 669, self.bas_w, self.bas_h),  (self.bas_x, 766, self.bas_w, self.bas_h)),
            ("entrada_intermedia",  (self.bas_x, 928, self.bas_w, self.bas_h),  (self.bas_x, 1024, self.bas_w, self.bas_h)),
            ("salida_principal",    (self.bas_x, 1187, self.bas_w, self.bas_h), (self.bas_x, 1282, self.bas_w, self.bas_h)),
            ("entrada_justificada", (self.bas_x, 1446, self.bas_w, self.bas_h), (self.bas_x, 1540, self.bas_w, self.bas_h)),
            ("salida_justificada",  (self.bas_x, 1704, self.bas_w, self.bas_h), (self.bas_x, 1799, self.bas_w, self.bas_h)),
        ]
        
        # Coordenadas de Motivos
        self.mot_y, self.mot_w, self.mot_h_total = 1952, 62, 114 
        self.coords_motivo_c1 = (50, self.mot_y, self.mot_w, self.mot_h_total)
        self.coords_motivo_c2 = (374, self.mot_y, self.mot_w, self.mot_h_total)
        self.etiq_motivo_c1 = ["MEDICO", "COMISION"]
        self.etiq_motivo_c2 = ["PERSONAL", "OTRO"]

        # Etiquetas Base
        self.etiquetas_horas = [str(h).zfill(2) for h in range(7, 19)]
        self.etiquetas_minutos = [str(m).zfill(2) for m in range(0, 60, 5)]

    # 2. MÉTODOS DE ALINEACIÓN (PERSPECTIVA Y MARCAS)
    
    def _ordenar_puntos(self, puntos):
        """Ordena 4 puntos: Arriba-Izq, Arriba-Der, Abajo-Der, Abajo-Izq"""
        rect = np.zeros((4, 2), dtype="float32")
        s = puntos.sum(axis=1)
        rect[0] = puntos[np.argmin(s)]
        rect[2] = puntos[np.argmax(s)]
        diff = np.diff(puntos, axis=1)
        rect[1] = puntos[np.argmin(diff)]
        rect[3] = puntos[np.argmax(diff)]
        return rect

    def _alinear_documento(self, imagen_cv, ancho_dest=1600, alto_dest=2200):
        """Busca las marcas de registro y devuelve la imagen estandarizada y binarizada"""
        gris = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
        # Desenfoque para ignorar ruido pequeño del papel
        suave = cv2.GaussianBlur(gris, (5, 5), 0)
        
        # Binarización aplicada sobre la imagen suavizada
        _, umbral = cv2.threshold(suave, 150, 255, cv2.THRESH_BINARY_INV)
        contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        centros_marcas = []
        for c in contornos:
            peri = cv2.arcLength(c, True)
            aprox = cv2.approxPolyDP(c, 0.04 * peri, True)
            area = cv2.contourArea(c)
            
            # Filtro estricto de Área 
            if len(aprox) == 4 and 1000 < area < 3500:
                x, y, w, h = cv2.boundingRect(aprox)
                aspect_ratio = float(w) / h
                solidez = area / float(w * h) 
                
                # Validar que sea un cuadrado perfecto y sólido
                if 0.85 <= aspect_ratio <= 1.15 and solidez > 0.8: 
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        centros_marcas.append([cx, cy])
                        
        # Selector inteligente de esquinas
        if len(centros_marcas) > 4:
            logging.warning(f"OMR: Se encontraron {len(centros_marcas)} marcas. Eliminando ruido...")
            pts_origen = self._ordenar_puntos(np.array(centros_marcas))
        elif len(centros_marcas) == 4:
            pts_origen = self._ordenar_puntos(np.array(centros_marcas))
        else:
            logging.error(f"OMR: ¡ERROR CRÍTICO! Solo se encontraron {len(centros_marcas)} marcas válidas. Procediendo sin alinear.")
            _, bin_original = cv2.threshold(gris, 150, 255, cv2.THRESH_BINARY_INV)
            return bin_original, imagen_cv
            
        # Transformación de Perspectiva
        pts_destino = np.array([
            [0, 0],
            [ancho_dest - 1, 0],
            [ancho_dest - 1, alto_dest - 1],
            [0, alto_dest - 1]
        ], dtype="float32")
        
        matriz = cv2.getPerspectiveTransform(pts_origen, pts_destino)
        imagen_alineada = cv2.warpPerspective(imagen_cv, matriz, (ancho_dest, alto_dest))
        
        gris_alineada = cv2.cvtColor(imagen_alineada, cv2.COLOR_BGR2GRAY)
        _, binarizada_alineada = cv2.threshold(gris_alineada, 150, 255, cv2.THRESH_BINARY_INV)
        
        return binarizada_alineada, imagen_alineada

    # 3. MÉTODOS DE LECTURA Y EXTRACCIÓN

    def _leer_qr(self, imagen_cv):
        """Extrae y decodifica el JSON del código QR."""
        codigos = decode(imagen_cv)
        for codigo in codigos:
            datos_texto = codigo.data.decode('utf-8')
            try:
                return json.loads(datos_texto)
            except json.JSONDecodeError:
                logging.error("OMR: El QR detectado no contiene un JSON válido.")
                return None
        return None

    def _verificar_firma(self, imagen_bin, umbral_pixeles=350):
        """Verifica si la zona de la firma tiene suficiente tinta."""
        x, y, w, h = self.coords_firma
        roi_firma = imagen_bin[y:y+h, x:x+w]
        pixeles_tinta = cv2.countNonZero(roi_firma)
        return pixeles_tinta > umbral_pixeles

    def _extraer_marcacion(self, imagen_bin, coords_fila, num_opciones, etiquetas, orientacion='H'):
        """Analiza burbujas y retorna la etiqueta de la que esté rellenada."""
        x, y, w, h = coords_fila
        marcas_encontradas = []
        
        if orientacion == 'H':
            paso = w // num_opciones
            for i in range(num_opciones):
                bx, by, bw, bh = x + (i * paso), y, paso, h
                roi_burbuja = imagen_bin[by:by+bh, bx:bx+bw]
                if cv2.countNonZero(roi_burbuja) > 1100: 
                    marcas_encontradas.append(etiquetas[i])
                    
        elif orientacion == 'V':
            paso = h // num_opciones
            for i in range(num_opciones):
                bx, by, bw, bh = x, y + (i * paso), w, paso
                roi_burbuja = imagen_bin[by:by+bh, bx:bx+bw]
                if cv2.countNonZero(roi_burbuja) > 1250: 
                    marcas_encontradas.append(etiquetas[i])
                    
        return marcas_encontradas[0] if marcas_encontradas else None

    # 4. PUNTO DE ENTRADA PRINCIPAL

    def procesar_documento(self, ruta_pdf):
        
    #   Retorna un diccionario con: {"estado": "OK"/"ERROR", "mensaje": "...", "datos": {...}}
       
        try:
            # 1. Carga inicial y validación de páginas
            paginas = convert_from_path(ruta_pdf, dpi=200)

            # Rechazar si hay más de 1 página
            if len(paginas) > 1:
                return {
                    "estado": "ERROR", 
                    "mensaje": f"El documento tiene {len(paginas)} páginas. Por favor, asegúrate de escanear y subir únicamente la hoja de asistencia (1 página)."
                }

            imagen_cv_cruda = cv2.cvtColor(np.array(paginas[0]), cv2.COLOR_RGB2BGR)
            
            # 2. Alineación y Binarización Automática
            binarizada, imagen_cv = self._alinear_documento(imagen_cv_cruda)

            # 3. Validación de QR
            datos_qr = self._leer_qr(imagen_cv)
            if not datos_qr:
                return {"estado": "ERROR", "mensaje": "No se detectó un código QR válido en el documento."}
            
            if datos_qr.get("tipo_archivo") != "OMR_ASISTENCIA_DIARIA":
                return {"estado": "ERROR", "mensaje": "El documento escaneado no es una hoja de asistencia válida."}

            # Extraer y limpiar el ID del empleado para la base de datos
            try:
                # Extraemos el número de "EMP-00003" -> "00003" -> 3
                id_qr_str = datos_qr.get("id", "").split("-")[1]
                id_usuario_limpio = int(id_qr_str)
            except Exception:
                return {"estado": "ERROR", "mensaje":"El formato del ID en el QR es inválido o no se pudo leer."}

            # 5. Validación de Firma
            if not self._verificar_firma(binarizada):
                return {"estado": "ERROR", "mensaje": "El documento no está firmado. Por favor fímalo antes de escanearlo."}

            # 6. Escaneo OMR
            datos_procesados = {
                "empleado_id": datos_qr.get("id"),
                "id_usuario": id_usuario_limpio, # Para la base de datos
                "fecha_documento": datos_qr.get("fecha"),
                "entradas_salidas": {},
                "motivo_justificacion": None
            }

            # A. Horarios
            for nombre_seccion, coords_h, coords_m in self.secciones_horarios:
                hora = self._extraer_marcacion(binarizada, coords_h, 12, self.etiquetas_horas, 'H')
                minuto = self._extraer_marcacion(binarizada, coords_m, 12, self.etiquetas_minutos, 'H')
                
                if hora and minuto:
                    datos_procesados["entradas_salidas"][nombre_seccion] = f"{hora}:{minuto}"
                else:
                    datos_procesados["entradas_salidas"][nombre_seccion] = None

            # B. Motivos
            motivo_1 = self._extraer_marcacion(binarizada, self.coords_motivo_c1, 2, self.etiq_motivo_c1, 'V')
            motivo_2 = self._extraer_marcacion(binarizada, self.coords_motivo_c2, 2, self.etiq_motivo_c2, 'V')
            motivo_final = motivo_1 if motivo_1 else motivo_2
            datos_procesados["motivo_justificacion"] = motivo_final

            # 7. Reglas de Negocio Básicas
            tiene_ent_just = datos_procesados["entradas_salidas"]["entrada_justificada"] is not None
            tiene_sal_just = datos_procesados["entradas_salidas"]["salida_justificada"] is not None

            if (tiene_ent_just or tiene_sal_just) and not motivo_final:
                return {"estado": "ERROR", "mensaje": "Marcaste horas justificadas, pero olvidaste rellenar el motivo."}

            # Si pasa todas las validaciones
            return {
                "estado": "OK",
                "mensaje": "Documento analizado con éxito.",
                "datos": datos_procesados
            }

        except Exception as e:
            logging.error(f"Error crítico en OMREngine: {str(e)}")
            return {"estado": "ERROR", "mensaje": "Error procesando la imagen. Asegúrate de escanearlo recto y en A4."}