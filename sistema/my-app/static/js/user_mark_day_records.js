document.addEventListener('alpine:init', () => {
    
    // COMPONENTE 1: BUSCADOR REACTIVO (Dropdowns de Mes, Año y Nombres)

    Alpine.data('formBuscador', (initialMes, initialBusqueda, apiFetchUrl) => ({
        // Variables de estado
        mesCompleto: initialMes, // Guarda el formato YYYY-MM para enviar al backend
        mesTemp: initialMes ? initialMes.split('-')[1] : '', // Extrae el mes (ej: '03')
        anioTemp: initialMes ? initialMes.split('-')[0] : '', // Extrae el año (ej: '2026')
        
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
        // Aquí vive el historial completo del mes, traído desde Flask
        todosLosRegistros: {}, 
        
        // Rastrea qué días específicos han sido alterados en el frontend
        fechasModificadas: [],
        hayCambiosGuardados: false, // Activa el botón verde grande de "Aplicar Cambios"
        isSaving: false, // Controla la pantalla de carga al aplicar cambios

        // --- VARIABLES VISUALES DEL MODAL ---
        modalAbierto: false,
        modalFecha: '', // Ej: '2026-03-15'
        modalFechaDisplay: '', // Ej: 'LUNES, 2026-03-15' (Para mostrar al usuario)
        modalMarcaciones: [], // Copia de trabajo de las marcas del día actual
        registrosConError: [],

        datosUsuario: null,

        // --- FUNCIÓN: Dispara el parpadeo rojo MODAL ---
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
            // Flask manda un diccionario gigante con todas las marcas. Lo copiamos.
            // Recibe los datos de Python y los hace suyos
            this.todosLosRegistros = JSON.parse(JSON.stringify(datosIniciales || {}));
            this.datosUsuario = datosUsuarioRecibidos;

            // datos del los registros (JSON)
            
            console.log("Datos del Funcionario:", this.datosUsuario);
            console.log("Estructura del JSON cargado:", this.todosLosRegistros);

            // Escanear la data que llega al inicio desde el backend para pintar las inconsistencias individuales
            this.marcarDuplicadosIniciales();
            
            // --- NUEVO: LEER ESTADOS REALES  ---
            // Leemos la columna 'tipoValidacion' que Python metió en cada 'marca.estado'
            for (let fecha in this.todosLosRegistros) {
                let marcasDelDia = this.todosLosRegistros[fecha];
                
                // La BD nos dice que este día ya fue validado o actualizado en el pasado
                let tieneActualizado = marcasDelDia.some(m => m.estado === 'Actualizado');
                let tieneValido = marcasDelDia.some(m => m.estado === 'Válido');
                
                // 1. Si vino como Actualizado, lo metemos a la memoria de modificaciones
                if (tieneActualizado && !this.fechasModificadas.includes(fecha)) {
                    this.fechasModificadas.push(fecha);
                }
                
                // 2. Si vino como Válido o Actualizado, CERRAMOS EL CANDADO (lo confirmamos visualmente)
                if ((tieneValido || tieneActualizado) && !this.fechasConfirmadas.includes(fecha)) {
                    this.fechasConfirmadas.push(fecha);
                }
            }

            // Escuchamos cuando el usuario hace click en el lápiz de cualquier tabla
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
                
                // Si encontramos un repetido o la cantidad del dia es invalida, marcamos todo como 'Inconsistente'
                this.todosLosRegistros[fecha].forEach(m => {
                    if (m.estado !== 'Descartado') {
                        if (conteosTipos[m.tipo] > 1 || conteosHoras[m.hora] > 1 || cantidadInvalida) {
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

                if ((marcas.length % 2 === 0) && !tieneDuplicados) {
                    // --- NUEVA JERARQUÍA QUE RESPETA EL ESTADO 'ACTUALIZADO' DE LA BD ---
                    if (this.fechasModificadas.includes(fecha) && this.fechasConfirmadas.includes(fecha)) {
                        estados.add('Actualizado');
                    } else if (this.fechasConfirmadas.includes(fecha)) {
                        estados.add('Válido');
                    } else {
                        estados.add('Por Validar');
                    }
                } else {
                    estados.add('Inconsistente');
                }
            }
            // Si hay Inconsistencia, gana y sobreescribe cualquier otro estado
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
                console.log(`Día ${fecha} CONFIRMADO:`, this.todosLosRegistros[fecha]);
            }
            
            // Registrar que el check verde cuenta como una modificación a guardar
            if (!this.fechasModificadas.includes(fecha)) {
                this.fechasModificadas.push(fecha);
            }
            this.hayCambiosGuardados = true; 
            // ------------------------------------------------------------------------

            console.log(`Progreso: ${this.diasListos()} de ${Object.keys(this.todosLosRegistros).length} días listos.`);
        },

        // --- FUNCIÓN: Cuenta cuántos días están listos para enviarse ---
        diasListos() {
            let count = 0;
            // Recorremos todas las fechas cargadas
            for (let fecha in this.todosLosRegistros) {
                // Obtenemos qué dice su etiqueta principal en la tabla
                let estados = this.obtenerEstadosDia(fecha);
                
                // Si la etiqueta dice Válido o Actualizado, lo contamos como listo
                if (estados.includes('Válido') || estados.includes('Actualizado')) {
                    count++;
                }
            }
            return count;
        },

        // Verifica si el total de días en la tabla es igual al total de checks dados
        todasConfirmadas() {
            const totalDias = Object.keys(this.todosLosRegistros).length;
            return totalDias > 0 && this.diasListos() === totalDias;
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
                
                // 1. Lógica de Jornada (Entrada primero)
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
            // En lugar de un rechazo silencioso, avisamos al usuario si no hay nada que guardar
            if (this.fechasModificadas.length === 0) {
                this.notificar("No se han detectado modificaciones nuevas para guardar.", "info");
                return;
            }

            // Bloquear pantalla
            this.isSaving = true;

            // Preparar el payload
            let payload = {
                id_funcionario: this.datosUsuario ? this.datosUsuario.nombres : null,
                mes_completo: document.querySelector('input[name="mes"]').value, // Ej: "2026-03"
                fechas_modificadas: {}
            };

            // Empaquetar solo los días que el usuario tocó (con lápiz o con check)
            this.fechasModificadas.forEach(fecha => {
                payload.fechas_modificadas[fecha] = this.todosLosRegistros[fecha];
            });

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