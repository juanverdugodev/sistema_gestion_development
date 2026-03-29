document.addEventListener('alpine:init', () => {
    
    // COMPONENTE 1: BUSCADOR REACTIVO (Dropdowns de Mes, Año y Nombres)

    Alpine.data('formBuscador', (initialMes, initialBusqueda, apiFetchUrl) => ({
        // Variables de estado
        mesCompleto: initialMes, // Guarda el formato YYYY-MM para enviar al backend
        mesTemp: initialMes ? initialMes.split('-')[1] : '', // Extrae el mes (ej: '03')
        anioTemp: initialMes ? initialMes.split('-')[0] : '', // Extrae el año (ej: '2026')
        
        // --- NUEVO: Mapa para traducir el mes en el botón personalizado ---
        nombresMeses: { '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril', '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto', '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre' },

        nombres: [], // Lista donde guardaremos los nombres devueltos por el backend
        
        loadingNames: false, // Controla si se muestra el ícono de "cargando"
        nombreSeleccionado: initialBusqueda, // Guarda el empleado actualmente elegido

        init() {
            // PASO 1: Si el usuario ya había buscado algo y la página se recargó, 
            // volvemos a llenar la lista de nombres automáticamente.
            if (this.mesCompleto) {
                this.fetchNombres();
            }
        },

        actualizarMesAnio() {
            // PASO 2: Validar la entrada del usuario.
            // Si el usuario ya eligió tanto el Mes como el Año en los selectores...
            if(this.mesTemp && this.anioTemp) {
                // Unimos las variables (Ej: '2026' + '-' + '03')
                this.mesCompleto = this.anioTemp + '-' + this.mesTemp;
                
                // Borramos el nombre seleccionado anteriormente (por si cambió de mes)
                this.nombreSeleccionado = '';
                
                // Llamamos a Flask para buscar los nuevos nombres
                this.fetchNombres();
            } else {
                // Si borró el año o el mes, bloqueamos y limpiamos todo
                this.mesCompleto = '';
                this.nombres = [];
            }
        },

        fetchNombres() {
            // PASO 3: Consumo de la API (Petición AJAX a Flask)
            if(!this.mesCompleto) { 
                this.nombres = []; 
                return; 
            }
            
            // Mostramos el spinner de carga
            this.loadingNames = true;
            
            // Hacemos la petición GET a la URL de Flask enviándole el mes
            // this.mesCompleto es "2026-03"
            fetch(`${apiFetchUrl}?mes=${this.mesCompleto}`)
            .then(res => res.json())
            .then(data => {
                // PASO 4: Procesar la respuesta del Backend
                if(data.exists) { 
                    // Llena el menú desplegable del HTML con los nombres de Python
                    this.nombres = data.names; 
                } else { 
                    // Si no existe, vaciamos la lista y alertamos al usuario
                    this.nombres = []; 
                    this.nombreSeleccionado = '';
                    
                    window.dispatchEvent(new CustomEvent('notify', { 
                        detail: { message: 'No hay datos cargados para este mes.', type: 'warning' }
                    }));
                }
            })
            .catch(err => console.error("Error consultando API:", err))
            .finally(() => {
                // Ocultamos el spinner de carga sin importar si hubo éxito o error
                this.loadingNames = false;
            });
        }
    }));


    // COMPONENTE 2: MODAL DE EDICIÓN DE JORNADAS

    Alpine.data('editorMarcaciones', (datosIniciales, datosUsuarioRecibidos) => ({
        
        // --- MEMORIA CENTRAL ---
        // Historial completo del mes, traído desde Flask
        todosLosRegistros: {}, 
        
        // Rastrea qué días específicos han sido alterados en el frontend
        fechasModificadas: [],
        hayCambiosGuardados: false, // Activa el botón verde de "Aplicar Cambios"
        isSaving: false, // Controla la pantalla de carga al aplicar cambios

        // --- VARIABLES VISUALES DEL MODAL ---
        modalAbierto: false,
        modalFecha: '', // Ej: '2026-03-15'
        modalFechaDisplay: '', // Ej: 'LUNES, 2026-03-15' (Para mostrar al usuario)
        modalMarcaciones: [], // Copia de trabajo de las marcas del día actual
        registrosConError: [],

        datosUsuario: null,

        modalGraficaAbierto: false, // Controla el modal de la imagen

        // --- Validar orden lógico del horario oficial ---
        validarOrdenHoras(campoModificado) {
            // Si falta alguno de los dos, no podemos comparar aún, pero sí marcamos que hubo un cambio
            if (!this.datosUsuario.entrada_oficial || !this.datosUsuario.salida_oficial) {
                this.hayCambiosGuardados = true;
                return;
            }

            let minEntrada = this.obtenerMinutos(this.datosUsuario.entrada_oficial);
            let minSalida = this.obtenerMinutos(this.datosUsuario.salida_oficial);

            // Si la entrada es a la misma hora o después de la salida, es un error
            if (minEntrada >= minSalida) {
                this.notificar("Incoherencia: La hora de Entrada no puede ser igual o posterior a la Salida.", "error");
                
                // Borramos el campo incorrecto para obligar al auditor a corregirlo
                if (campoModificado === 'entrada') {
                    this.datosUsuario.entrada_oficial = '';
                } else {
                    this.datosUsuario.salida_oficial = '';
                }
                // Al vaciarse el campo, el candado de confirmación se bloqueará automáticamente
            } else {
                // Si todo está correcto, activamos el botón de guardar
                this.hayCambiosGuardados = true;
            }
        },

        // --- Verifica si los 3 campos del horario base están llenos ---
        horarioCompleto() {
            if (!this.datosUsuario) return false;
            
            const ent = this.datosUsuario.entrada_oficial;
            const sal = this.datosUsuario.salida_oficial;
            const rec = this.datosUsuario.receso_oficial;
            
            // Retorna true solo si los 3 campos tienen algún valor escrito
            return !!ent && !!sal && !!rec;
        },

        // --- Candado del Horario Oficial ---
        toggleConfirmarHorario() {
            this.datosUsuario.horarioConfirmado = !this.datosUsuario.horarioConfirmado;
            
            // Al confirmar (cerrar el candado), lo marcamos visualmente como oficial (ícono verde)
            if (this.datosUsuario.horarioConfirmado) {
                this.datosUsuario.es_oficial = true;
            }
            
            // Activa el botón verde principal de "Aplicar Cambios" para enviar a Python
            this.hayCambiosGuardados = true;
        },

        // --- Fuerza el formato 24H visualmente
        formatearHora24(evento, obj, propiedad) {
            let valor = evento.target.value.replace(/\D/g, ''); // Elimina letras/símbolos
            
            if (valor.length >= 3) {
                valor = valor.substring(0, 2) + ':' + valor.substring(2, 4);
            }
            
            // Validar que no pongan horas irreales (ej: 25:99)
            if (valor.length === 5) {
                let partes = valor.split(':');
                let h = parseInt(partes[0], 10);
                let m = parseInt(partes[1], 10);
                
                if (h > 23) h = 23;
                if (m > 59) m = 59;
                
                valor = h.toString().padStart(2, '0') + ':' + m.toString().padStart(2, '0');
            }
            
            obj[propiedad] = valor;
            this.hayCambiosGuardados = true; // Activa el botón de guardar automáticamente
        },

        // --- MATEMÁTICA DE ATRASOS Y SALIDAS ANTICIPADAS ---

        // 1. Convierte formato HH:mm a minutos totales para poder restar
        obtenerMinutos(horaStr) {
            if (!horaStr || !horaStr.includes(':')) return 0;
            let [h, m] = horaStr.split(':').map(Number);
            return (h * 60) + m;
        },

        // 2. Calcula el descuento individual evaluando el tipo de marca
        calcularPenalizacionMarca(marca, fecha) {
            if (!this.datosUsuario) return null;
            if (marca.estado === 'Descartado') return null;

            if (marca.tipo === 'Entrada') {
                if (!this.datosUsuario.entrada_oficial) return null;
                let minOficialEntrada = this.obtenerMinutos(this.datosUsuario.entrada_oficial);
                let minMarca = this.obtenerMinutos(marca.hora);
                let atraso = minMarca - minOficialEntrada;
                return atraso > 0 ? Number(atraso) : 0;
            }
            
            if (marca.tipo === 'Salida') {
                if (!this.datosUsuario.salida_oficial) return null;
                let minOficialSalida = this.obtenerMinutos(this.datosUsuario.salida_oficial);
                let minMarca = this.obtenerMinutos(marca.hora);
                let salidaAnticipada = minOficialSalida - minMarca;
                return salidaAnticipada > 0 ? Number(salidaAnticipada) : 0;
            }

            if (marca.tipo === 'Salida Almuerzo') {
                if (!this.datosUsuario.receso_oficial) return null;
                return 0; // Retorna 0 para mostrar la etiqueta azul "Inicia Receso" sin penalizar
            }

            if (marca.tipo === 'Regreso Almuerzo') {
                if (!this.datosUsuario.receso_oficial) return null;
                
                // Buscar a qué hora salió a almorzar este mismo día
                let marcasDia = this.obtenerMarcasActivas(fecha);
                let salidaAlmuerzo = marcasDia.find(m => m.tipo === 'Salida Almuerzo');
                
                if (!salidaAlmuerzo) return 0; // Si no hay salida de almuerzo, no se puede calcular

                let minSalidaAlm = this.obtenerMinutos(salidaAlmuerzo.hora);
                let minRegresoAlm = this.obtenerMinutos(marca.hora);
                
                let duracionReal = minRegresoAlm - minSalidaAlm;
                let duracionPermitida = this.obtenerMinutos(this.datosUsuario.receso_oficial);
                
                let exceso = duracionReal - duracionPermitida;
                
                // Forzamos estrictamente a que retorne un número real
                return exceso > 0 ? Number(exceso) : 0; 
            }

            return null; // Si es Comisión, lo ignora
        },

        // --- NUEVA FUNCIÓN: Mantiene el HTML limpio ---
        textoPenalizacion(marca, fecha) {
            let pen = this.calcularPenalizacionMarca(marca, fecha);
            if (pen === null) return '';
            
            if (pen > 0) {
                if (marca.tipo === 'Entrada') return `Atraso: ${pen}m`;
                if (marca.tipo === 'Salida') return `Anticipada: ${pen}m`;
                if (marca.tipo === 'Regreso Almuerzo') return `Exceso: ${pen}m`;
            } else {
                if (marca.tipo === 'Entrada') return 'Sin atraso';
                if (marca.tipo === 'Salida') return 'Salida OK';
                if (marca.tipo === 'Salida Almuerzo') return 'Inicia Receso';
                if (marca.tipo === 'Regreso Almuerzo') return 'Receso OK';
            }
            return '';
        },

        // 3. Suma el total del día 
        calcularPenalizacionDia(fecha) {
            let marcas = this.obtenerMarcasActivas(fecha);
            let totalDia = 0;
            let tieneCalculo = false;

            marcas.forEach(m => {
                let penalizacion = this.calcularPenalizacionMarca(m, fecha);
                if (penalizacion !== null) {
                    // REFUERZO MATEMÁTICO: Obligamos a JS a sumar números, no textos
                    totalDia += Number(penalizacion); 
                    tieneCalculo = true;
                }
            });
            
            return tieneCalculo ? totalDia : null;
        },

        // 4. Suma el total del mes y lo formatea a HH:MM
        calcularPenalizacionMensual() {
            if (!this.datosUsuario || !this.datosUsuario.entrada_oficial || !this.datosUsuario.salida_oficial) return null;
            
            let totalGlobal = 0;
            for (let fecha in this.todosLosRegistros) {
                // Solo suma si el día fue auditado (Válido o Actualizado)
                let estados = this.obtenerEstadosDia(fecha);
                if (estados.includes('Válido') || estados.includes('Actualizado')) {
                    let penDia = this.calcularPenalizacionDia(fecha);
                    if (penDia !== null) totalGlobal += penDia;
                }
            }
            return totalGlobal;
        },

        // Formateador visual (pasa de 65 min a "01:05")
        formatearMinutos(totalMinutos) {
            if (totalMinutos === null) return '--:--';
            let h = Math.floor(totalMinutos / 60);
            let m = totalMinutos % 60;
            return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
        },

        // ------------------------------------------------------------------

        // --- Conteo de días asistidos ---
        
        // --- NUEVO: Extraer penalizaciones diarias para el Backend ---
        obtenerPenalizacionesDia(fecha) {
            let marcas = this.obtenerMarcasActivas(fecha);
            let atrasoEnt = 0;
            let atrasoAlm = 0;
            let atrasoSal = 0;

            marcas.forEach(m => {
                let pen = this.calcularPenalizacionMarca(m, fecha);
                if (pen !== null && pen > 0) {
                    if (m.tipo === 'Entrada') atrasoEnt += pen;
                    if (m.tipo === 'Salida') atrasoSal += pen;
                    if (m.tipo === 'Regreso Almuerzo') atrasoAlm += pen;
                }
            });

            return {
                atrasoEntrada: this.formatearMinutos(atrasoEnt),
                atrasoAlmuerzo: this.formatearMinutos(atrasoAlm),
                atrasoSalida: this.formatearMinutos(atrasoSal)
            };
        },
        
        // Retorna el total de días que existen en el JSON de este mes
        totalDiasMes() {
            return Object.keys(this.todosLosRegistros).length;
        },

        // Retorna cuántos días tienen al menos una marca no descartada
        diasAsistidos() {
            let asistencias = 0;
            for (let fecha in this.todosLosRegistros) {
                let marcasDelDia = this.todosLosRegistros[fecha];
                // Buscamos si hay alguna marca que NO sea 'Descartado'
                let diaActivo = marcasDelDia.some(m => m.estado !== 'Descartado');
                if (diaActivo) {
                    asistencias++;
                }
            }
            return asistencias;
        },
        
        // --- Dispara el parpadeo rojo MODAL ---
        marcarErroresVisuales(idsRegistros, mensaje) {
            this.registrosConError = idsRegistros;
            this.notificar(mensaje, "error");
            
            // Quita el parpadeo rojo después de 5.5 segundos
            setTimeout(() => {
                this.registrosConError = [];
            }, 5500);
        },

        // Disparador de Alertas visuales
        notificar(mensaje, tipo = 'info') {
            window.dispatchEvent(new CustomEvent('notify', {
                detail: { message: mensaje, type: tipo }
            }));
        },

        init() {
            // PASO 1: Inyectar datos iniciales
            this.todosLosRegistros = JSON.parse(JSON.stringify(datosIniciales || {}));
            this.datosUsuario = datosUsuarioRecibidos;

            console.log("Datos del Funcionario:", this.datosUsuario);
            console.log("Estructura del JSON cargado:", this.todosLosRegistros);

            // --- NUEVO: Estado del candado del horario base ---
            if (this.datosUsuario) {
                // Si ya era un dato oficial (auditado), aparece bloqueado por defecto.
                this.datosUsuario.horarioConfirmado = this.datosUsuario.es_oficial || false;
            }
            // --------------------------------------------------

            // Escanear la data que llega al inicio desde el backend para pintar las inconsistencias individuales
            this.marcarDuplicadosIniciales();
            
            // --- REAURADO: LEER ESTADOS REALES DESDE LA BASE DE DATOS ---
            for (let fecha in this.todosLosRegistros) {
                let marcasDelDia = this.todosLosRegistros[fecha];
                
                // La BD nos dice si este día ya tiene marcas validadas o actualizadas
                let tieneActualizado = marcasDelDia.some(m => m.estado === 'Actualizado');
                let tieneValido = marcasDelDia.some(m => m.estado === 'Válido');
                
                // 1. Si vino como Actualizado, lo metemos a la memoria de modificaciones
                if (tieneActualizado && !this.fechasModificadas.includes(fecha)) {
                    this.fechasModificadas.push(fecha);
                }
                
                // 2. Si vino como Válido o Actualizado desde el JSON, CERRAMOS EL CANDADO
                if ((tieneValido || tieneActualizado) && !this.fechasConfirmadas.includes(fecha)) {
                    this.fechasConfirmadas.push(fecha);
                }
            }

            // RESTAURADO: Escuchar cuando el usuario hace click en el lápiz
            this.$el.addEventListener('abrir-modal', (e) => {
                this.abrirModalEdicion(e.detail.fecha, e.detail.dia);
            });
        },

        // FUNCIONES REACTIVAS PARA LA TABLA PRINCIPAl
        // --- FUNCIÓN AUTOMÁTICA DETECTAR INCONSISTENCIAS ---

        marcarDuplicadosIniciales() {
            // Recorremos todos los dias cargados en la memoria
            for (let fecha in this.todosLosRegistros) {
                let marcasActivas = this.todosLosRegistros[fecha].filter(m => m.estado !== 'Descartado');
                
                // Contadores para encontrar repeticiones
                let conteosTipos = {};
                let conteosHoras = {};
                
                marcasActivas.forEach(m => {
                    conteosTipos[m.tipo] = (conteosTipos[m.tipo] || 0) + 1;
                    conteosHoras[m.hora] = (conteosHoras[m.hora] || 0) + 1;
                });
                
                // Evaluamos si el dia tiene una cantidad impar de marcas
                let cantidadInvalida = (marcasActivas.length > 0 && marcasActivas.length % 2 !== 0);

                // --- NUEVA LÓGICA INFALIBLE PARA 2 MARCAS ---
                // Si hay 2 marcas, TIENEN que ser Entrada y Salida. Si falta alguna, es inconsistente.
                let tiposActivos = marcasActivas.map(m => m.tipo);
                let combinacionInvalida2Marcas = (marcasActivas.length === 2 && 
                                                  !(tiposActivos.includes('Entrada') && tiposActivos.includes('Salida')));
                
                // Si encontramos un repetido, cantidad impar, o un combo inválido de 2 marcas, marcamos todo
                this.todosLosRegistros[fecha].forEach(m => {
                    if (m.estado !== 'Descartado') {
                        if (conteosTipos[m.tipo] > 1 || conteosHoras[m.hora] > 1 || cantidadInvalida || combinacionInvalida2Marcas) {
                            m.estado = 'Inconsistente';
                        }
                    }
                });
            }
        },

        obtenerMarcasActivas(fecha) {
            // Devuelve las marcas de ese día que no estén descartadas
            if (!this.todosLosRegistros[fecha]) return [];
            return this.todosLosRegistros[fecha].filter(m => m.estado !== 'Descartado');
        },

        obtenerEstadosDia(fecha) {
            let marcas = this.obtenerMarcasActivas(fecha);
            let estados = new Set();
            
            if (marcas.length > 0) {
                let tipos = marcas.map(m => m.tipo);
                let tieneDuplicados = tipos.length !== new Set(tipos).size;

                // --- SINCRONIZADO CON LA REGLA INFALIBLE ---
                let combinacionInvalida2Marcas = (marcas.length === 2 && 
                                                  !(tipos.includes('Entrada') && tipos.includes('Salida')));
                
                let tieneMarcasInconsistentes = marcas.some(m => m.estado === 'Inconsistente');

                // Si pasa todas las validaciones estructurales...
                if ((marcas.length % 2 === 0) && !tieneDuplicados && !combinacionInvalida2Marcas && !tieneMarcasInconsistentes) {
                    
                    let tieneActualizado = marcas.some(m => m.estado === 'Actualizado');

                    if (this.fechasConfirmadas.includes(fecha)) {
                        if (tieneActualizado) {
                            estados.add('Actualizado');
                        } else {
                            estados.add('Válido');
                        }
                    } else {
                        if (tieneActualizado) {
                            estados.add('Actualizado'); 
                        } else {
                            estados.add('Por Validar');
                        }
                    }

                } else {
                    // Si cae en la trampa, bloqueamos
                    estados.add('Inconsistente');
                }
            }
            
            if (estados.has('Inconsistente')) {
                estados.clear(); 
                estados.add('Inconsistente');
            }

            return Array.from(estados);
        },

        // --------------------

        // --- FUNCIONES AYUDANTES PARA EL HTML (Evitan que Alpine se congele) ---
        esInconsistente(fecha) {
            return this.obtenerEstadosDia(fecha).includes('Inconsistente');
        },

        esConfirmado(fecha) {
            return this.fechasConfirmadas.includes(fecha);
        },

                // --- MEMORIA DE CONFIRMACIÓN ---
        fechasConfirmadas: [], // Guarda los días que ya tienen el "check" verde

        // --- FUNCIONES DE CONFIRMACIÓN ---
        toggleConfirmarDia(fecha) {
            if (this.fechasConfirmadas.includes(fecha)) {
                // DESBLOQUEAR: Quitamos de la lista de candados cerrados
                this.fechasConfirmadas = this.fechasConfirmadas.filter(f => f !== fecha);
                
                // Si el día ya había sido tocado por un humano (fue modificado alguna vez),
                // al desbloquearlo no debería volver a 'Por Validar', porque sus datos no son los crudos.
                // En cambio, si era un día inmaculado, sí vuelve a 'Por Validar'.
                if (this.todosLosRegistros[fecha]) {
                    this.todosLosRegistros[fecha].forEach(marca => {
                        // Solo revertimos a 'Por Validar' si la marca era 'Válido' (inmaculada).
                        // Si era 'Actualizado', se queda como 'Actualizado' para no perder el rastro de la edición.
                        if (marca.estado === 'Válido') marca.estado = 'Por Validar';
                    });
                }
                console.log(`Día ${fecha} DESBLOQUEADO:`, this.todosLosRegistros[fecha]);
            } else {
                // CONFIRMAR: Añadimos a la lista (Cerramos el candado)
                this.fechasConfirmadas.push(fecha);
                
                // Si la persona le da "check" a la fila entera, evaluamos el estado de cada marca adentro
                if (this.todosLosRegistros[fecha]) {
                    this.todosLosRegistros[fecha].forEach(marca => {
                        // Si la marca no está descartada y era 'Por Validar' (cruda), pasa a 'Válido'.
                        // Si la marca era 'Actualizado' (editada a mano), se queda como 'Actualizado' ¡y no se baja de rango!
                        if (marca.estado !== 'Descartado' && marca.estado === 'Por Validar') {
                            marca.estado = 'Válido';
                        }
                    });
                }
                console.log(`Progreso: ${this.tareasCompletadas()} de ${this.tareasTotales()} validaciones listas.`);
            }
            
            // Registrar que el check verde cuenta como una modificación a guardar
            if (!this.fechasModificadas.includes(fecha)) {
                this.fechasModificadas.push(fecha);
            }
            this.hayCambiosGuardados = true; 
            // ------------------------------------------------------------------------

            console.log(`Progreso: ${this.diasListos()} de ${Object.keys(this.todosLosRegistros).length} días listos.`);
        },

        // Cuenta el total de acciones requeridas (Días en la tabla + 1 del Horario Principal)
        tareasTotales() {
            let total = Object.keys(this.todosLosRegistros).length;
            if (this.datosUsuario) total += 1; // Sumamos 1 por el candado del horario
            return total;
        },

        // Cuenta ESTRICTAMENTE cuántos candados (checks) están cerrados actualmente
        tareasCompletadas() {
            // Contamos los candados cerrados en la tabla (ya no nos fijamos en la etiqueta de texto)
            let completadas = this.fechasConfirmadas.length; 
            
            // Sumamos 1 si el candado del horario principal está cerrado
            if (this.datosUsuario && this.datosUsuario.horarioConfirmado) {
                completadas += 1;
            }
            return completadas;
        },

        // Verifica si todos los candados exigidos están cerrados
        todasConfirmadas() {
            const totales = this.tareasTotales();
            return totales > 0 && this.tareasCompletadas() === totales;
        },

        // Evalúa si se cumplen todas las condiciones para activar el botón verde
        puedeGuardar() {
            return this.todasConfirmadas() && this.hayCambiosGuardados;
        },

        // Cambia el texto del botón dinámicamente manteniendo un formato corto: "Validar (X/Y)"
        textoBotonGuardar() {
            if (!this.todasConfirmadas()) {
                return `Validar (${this.tareasCompletadas()}/${this.tareasTotales()})`;
            }
            if (!this.hayCambiosGuardados) {
                return 'Sin cambios';
            }
            return 'Guardar cambios';
        },

        

        abrirModalEdicion(fecha, nombreDia) {
            // PASO 2: Preparar la vista del Modal
            this.modalFecha = fecha;
            this.modalFechaDisplay = `${nombreDia.toUpperCase()}, ${fecha}`;
            
            // Si el día estaba vacío en BD, creamos una lista vacía para evitar errores
            if (!this.todosLosRegistros[fecha]) {
                this.todosLosRegistros[fecha] = [];
            }

            // CREAMOS UNA COPIA PROFUNDA: El usuario edita 'modalMarcaciones', no la memoria central.
            // Si cancela, los datos originales siguen intactos.
            this.modalMarcaciones = JSON.parse(JSON.stringify(this.todosLosRegistros[fecha]));
            
            this.modalAbierto = true; // Mostramos el pop-up
        },

        cerrarModal() {
            // Simplemente oculta el modal y destruye la copia de trabajo
            this.modalAbierto = false;
            this.modalMarcaciones = [];
        },

        alternarDescartado(index) {
            // PASO 3 (Interacción): Lógica del botón Papelera/Deshacer
            const marca = this.modalMarcaciones[index];
            if (marca.estado === 'Descartado') {
                marca.estado = 'Actualizado'; // Restaura
            } else {
                marca.estado = 'Descartado';  // Borra lógicamente (Soft Delete)
            }
        },

        // --- NUEVA FUNCIÓN: Memoria de validación ---
        toggleValidacionMarca(marca) {
            if (marca.estado === 'Válido') {
                // Si se arrepiente (quita el check), restaura el estado que guardamos.
                // Si por alguna razón no hay estado previo, el fallback seguro es 'Por Validar'.
                marca.estado = marca.estado_previo || 'Por Validar';
            } else {
                // Si va a validar (dar el check), primero guardamos una copia de lo que era
                // (ej. guarda 'Inconsistente' o 'Por Validar') antes de pasarlo a Válido.
                marca.estado_previo = marca.estado;
                marca.estado = 'Válido';
            }
        },

        agregarNuevoRegistro() {
            // PASO 4 (Interacción): Limita a 6 marcas ACTIVAS máximo por día
            
            // Primero, contamos cuántas marcas no están en la papelera
            const marcasActivas = this.modalMarcaciones.filter(m => m.estado !== 'Descartado').length;

            // Si ya hay 6 marcas útiles, bloqueamos la creación
            if (marcasActivas >= 6) {
                this.notificar("La jornada ya cuenta con el límite de 6 marcaciones activas.", "warning");
                return;
            }
            
            // Inyecta una fila vacía estándar al final de la tabla
            this.modalMarcaciones.push({
                // Generamos un ID temporal único para que la animación roja no falle si este registro causa error
                id_registro: 'temp_' + Math.random().toString(36).substr(2, 9), 
                hora: '00:00',
                tipo: 'Entrada',
                estado: 'Actualizado', 
                metodo: 'MANUAL'
            });
        },

       guardarModal() {
            // Se crea una lista solo con las marcas activas (no descartadas) para el analisis
            const marcasActivasLista = this.modalMarcaciones.filter(m => m.estado !== 'Descartado');
            const marcasActivas = marcasActivasLista.length;

            // Regla 1: Debe haber al menos 2 marcas (no se permite 0) y debe ser un número par.
            if (marcasActivas === 0 || marcasActivas % 2 !== 0) {
                // Si dejaron en 0, iluminamos todos los registros del modal (aunque estén descartados).
                // Si es impar, iluminamos solo los que dejaron activos.
                let idsError = marcasActivas === 0 
                    ? this.modalMarcaciones.map(m => m.id_registro) 
                    : marcasActivasLista.map(m => m.id_registro);
                
                let mensajeError = marcasActivas === 0 
                    ? "Error: No se permite descartar todos los registros. La jornada debe tener al menos una Entrada y una Salida."
                    : `Inconsistencia: El día debe tener un número par de marcas (pares de entrada/salida). Actualmente existen ${marcasActivas} activas.`;

                this.marcarErroresVisuales(idsError, mensajeError);
                return; 
            }

            // Regla 2: Obligar a revisar todos los estados.
            // No se permite guardar si existen marcas activas con estado "Por Validar" o "Inconsistente".
            const marcasSinRevisar = marcasActivasLista.filter(m => 
                m.estado === 'Por Validar' || m.estado === 'Inconsistente'
            );

            if (marcasSinRevisar.length > 0) {
                // Extraemos los IDs exclusivamente de los registros que faltan por revisar
                let idsSinRevisar = marcasSinRevisar.map(m => m.id_registro);
                
                this.marcarErroresVisuales(
                    idsSinRevisar, 
                    "Aún existen registros 'Por Validar' o 'Inconsistentes'. Revise y asigne un estado válido a cada marcación resaltada."
                );
                return; 
            }

            // Regla 3: No permitir horas duplicadas exactas con animación visual.
            let horasVistas = {};
            for (let marca of marcasActivasLista) {
                if (horasVistas[marca.hora]) {
                    // Si la hora ya existe en nuestro registro, disparamos el error visual con ambos IDs
                    this.marcarErroresVisuales(
                        [horasVistas[marca.hora], marca.id_registro], 
                        `Error: Existen marcaciones con exactamente la misma hora (${marca.hora}). Por favor, cambie una o descártela.`
                    );
                    return; 
                }
                horasVistas[marca.hora] = marca.id_registro;
            }

            // Regla 4: No permitir tipos de marcas repetidos con animación visual.
            let tiposVistos = {};
            for (let marca of marcasActivasLista) {
                if (tiposVistos[marca.tipo]) {
                    // Si el tipo (ej. "Entrada") ya existe, disparamos el error visual con ambos IDs
                    this.marcarErroresVisuales(
                        [tiposVistos[marca.tipo], marca.id_registro], 
                        `Error: Tiene más de un registro de "${marca.tipo}" activo. Debe descartar uno o cambiar el tipo.`
                    );
                    return; 
                }
                tiposVistos[marca.tipo] = marca.id_registro;
            }

            // Paso 5: Cierre y guardado en memoria
            // A. Ordenar las marcas cronologicamente
            this.modalMarcaciones.sort((a, b) => a.hora.localeCompare(b.hora));

            // --- REGLAS LOGICAS DE EVENTOS EN EL TIEMPO CON ANIMACIÓN VISUAL ---
            const marcasOrdenadas = this.modalMarcaciones.filter(m => m.estado !== 'Descartado');
            if (marcasOrdenadas.length > 0) {
                
                // --- NUEVA REGLA: Bloqueo de 2 marcas (Entrada y Almuerzo) en el modal ---
                if (marcasOrdenadas.length === 2) {
                    const tieneEntrada = marcasOrdenadas.find(m => m.tipo === 'Entrada');
                    const tieneSalida = marcasOrdenadas.find(m => m.tipo === 'Salida');
                    
                    if (!tieneEntrada || !tieneSalida) {
                        // Buscamos cuál es la marca extraña para mostrarla en el mensaje de error
                        const marcaInvalida = marcasOrdenadas.find(m => m.tipo !== 'Entrada' && m.tipo !== 'Salida') || marcasOrdenadas[0];
                        
                        this.marcarErroresVisuales(
                            marcasOrdenadas.map(m => m.id_registro), 
                            `Incoherencia: Una jornada de 2 marcaciones debe ser estrictamente 'Entrada' y 'Salida'. Revisa el registro de '${marcaInvalida.tipo}'.`
                        );
                        return; // Bloquea el guardado
                    }
                }

                //  Lógica de Jornada (Entrada primero)
                const hayEntrada = marcasOrdenadas.find(m => m.tipo === 'Entrada');
                if (hayEntrada && marcasOrdenadas[0].tipo !== 'Entrada') {
                    this.marcarErroresVisuales([marcasOrdenadas[0].id_registro, hayEntrada.id_registro], "Incoherencia: El registro de 'Entrada' debe ser el primero del día. Las filas en conflicto están resaltadas.");
                    return; // Bloquea el guardado
                }
                
                // Lógica de Jornada (Salida al final)
                const haySalida = marcasOrdenadas.find(m => m.tipo === 'Salida');
                const ultimoRegistro = marcasOrdenadas[marcasOrdenadas.length - 1];
                if (haySalida && ultimoRegistro.tipo !== 'Salida') {
                    this.marcarErroresVisuales([ultimoRegistro.id_registro, haySalida.id_registro], "Incoherencia: El registro de 'Salida' final debe ser el último del día. Las filas en conflicto están resaltadas.");
                    return; // Bloquea el guardado
                }

                // 2. Lógica de Almuerzo (La salida debe ocurrir antes que el regreso)
                const regSalidaAlm = marcasOrdenadas.find(m => m.tipo === 'Salida Almuerzo');
                const regRegresoAlm = marcasOrdenadas.find(m => m.tipo === 'Regreso Almuerzo');
                
                if (regSalidaAlm && regRegresoAlm) {
                    if (marcasOrdenadas.indexOf(regSalidaAlm) > marcasOrdenadas.indexOf(regRegresoAlm)) {
                        this.marcarErroresVisuales([regSalidaAlm.id_registro, regRegresoAlm.id_registro], "Incoherencia: La 'Salida Almuerzo' no puede registrarse después del 'Regreso Almuerzo'.");
                        return; // Bloquea el guardado
                    }
                }

                // 3. Lógica de Comisión (La salida debe ocurrir antes que el regreso)
                const regSalidaCom = marcasOrdenadas.find(m => m.tipo === 'Salida Comisión');
                const regRegresoCom = marcasOrdenadas.find(m => m.tipo === 'Regreso Comisión');
                
                if (regSalidaCom && regRegresoCom) {
                    if (marcasOrdenadas.indexOf(regSalidaCom) > marcasOrdenadas.indexOf(regRegresoCom)) {
                        this.marcarErroresVisuales([regSalidaCom.id_registro, regRegresoCom.id_registro], "Incoherencia: La 'Salida Comisión' no puede registrarse después del 'Regreso Comisión'.");
                        return; // Bloquea el guardado
                    }
                }
            }
            // ------------------------------------------------

            // B. Pasar la copia de trabajo a la memoria central
            this.todosLosRegistros[this.modalFecha] = JSON.parse(JSON.stringify(this.modalMarcaciones));
            
            // C. Registrar que este dia fue modificado en la interfaz
            if (!this.fechasModificadas.includes(this.modalFecha)) {
                this.fechasModificadas.push(this.modalFecha);
            }
            
            // Activar el boton principal de aplicacion de cambios
            this.hayCambiosGuardados = true; 
            
            this.cerrarModal();

            // D. Auto-confirmar la fila en la tabla principal tras la edicion
            if (!this.fechasConfirmadas.includes(this.modalFecha)) {
                this.fechasConfirmadas.push(this.modalFecha);
            }

            this.notificar("Cambios guardados temporalmente. Revisa todos los registros y luego confirma el guardado con el boton Aplicar cambios.", "success");

            // JSON Actualizado segun los cambios
            console.log(`Día ${this.modalFecha} actualizado:`, this.todosLosRegistros[this.modalFecha]);
            console.log("Calendario completo actualizado:", this.todosLosRegistros);
        },

        aplicarCambiosServidor() {
            
            if (this.fechasModificadas.length === 0 && !this.hayCambiosGuardados) {
                this.notificar("No se han detectado modificaciones nuevas para guardar.", "info");
                return;
            }

            // Bloquear pantalla
            this.isSaving = true;

            // Preparar el payload
            let payload = {
                id_funcionario: this.datosUsuario ? this.datosUsuario.nombres : null,
                mes_completo: document.querySelector('input[name="mes"]').value, // Ej: "2026-03"
                fechas_modificadas: {},
                penalizaciones_diarias: {}, // Contenedor para los atrasos (Parquet 3)

                // --- Mandamos las horas oficiales editadas al servidor ---
                entrada_oficial: this.datosUsuario ? this.datosUsuario.entrada_oficial : null,
                salida_oficial: this.datosUsuario ? this.datosUsuario.salida_oficial : null,
                receso_oficial: this.datosUsuario ? this.datosUsuario.receso_oficial : null,

                // --- Mandamos la métrica del atraso total (Ej: "01:20") ---
                atraso_total: this.calcularPenalizacionMensual() !== null ? this.formatearMinutos(this.calcularPenalizacionMensual()) : null

            };

            // 1. Empaquetar solo los días que el usuario tocó manualmente (Para Parquet 1)
            this.fechasModificadas.forEach(fecha => {
                payload.fechas_modificadas[fecha] = this.todosLosRegistros[fecha];
            });

            // 2. NUEVO: Recalcular y empaquetar penalizaciones de TODOS los días (Para Parquet 3)
            // Así garantizamos que si se cambió el "Horario Oficial", se actualice toda la columna
            for (let fecha in this.todosLosRegistros) {
                payload.penalizaciones_diarias[fecha] = this.obtenerPenalizacionesDia(fecha);
            }

            console.log("Enviando JSON al servidor:", payload);

            // Enviar a Flask
            fetch('/api/guardar_edicion_jornada', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Recargar la página con un parámetro de éxito
                    window.location.href = window.location.pathname + window.location.search + '&success=true';
                } else {
                    this.isSaving = false;
                    this.notificar(data.error || "Error al guardar los datos.", "error");
                }
            })
            .catch(error => {
                console.error("Error crítico en fetch:", error);
                this.isSaving = false;
                this.notificar("Error de conexión al guardar los datos.", "error");
            });
        }

    }));
});