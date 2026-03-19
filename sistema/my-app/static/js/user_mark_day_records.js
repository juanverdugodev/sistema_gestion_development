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

        // --- VARIABLES VISUALES DEL MODAL ---
        modalAbierto: false,
        modalFecha: '', // Ej: '2026-03-15'
        modalFechaDisplay: '', // Ej: 'LUNES, 2026-03-15' (Para mostrar al usuario)
        modalMarcaciones: [], // Copia de trabajo de las marcas del día actual

        datosUsuario: null,

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
                
                // Evaluamos si el dia tiene una cantidad incorrecta de marcas (que no sea ni 4 ni 6)
                let cantidadInvalida = (marcasActivas.length > 0 && marcasActivas.length !== 4 && marcasActivas.length !== 6);
                
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
            // Ya usamos obtenerMarcasActivas, así que los "Descartados" están ignorados mágicamente
            let marcas = this.obtenerMarcasActivas(fecha);
            let estados = new Set();
            
            // Si hay 4 o 6 marcas activas, se asume que la jornada está completa.
            if (marcas.length > 0) {
                let tipos = marcas.map(m => m.tipo);
                let tieneDuplicados = tipos.length !== new Set(tipos).size;

                if ((marcas.length === 4 || marcas.length === 6) && !tieneDuplicados) {
                    // Jerarquía: Válido > Actualizado > Por Validar
                    if (this.fechasConfirmadas.includes(fecha)) {
                        estados.add('Válido');
                    } else if (this.fechasModificadas.includes(fecha)) {
                        estados.add('Actualizado');
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

        // --- NUEVAS FUNCIONES DE CONFIRMACIÓN ---
        toggleConfirmarDia(fecha) {
            if (this.fechasConfirmadas.includes(fecha)) {
                // DESBLOQUEAR: Quitamos de la lista
                this.fechasConfirmadas = this.fechasConfirmadas.filter(f => f !== fecha);
                
                // Retornar a 'Por Validar' adentro del modal
                if (this.todosLosRegistros[fecha]) {
                    this.todosLosRegistros[fecha].forEach(marca => {
                        if (marca.estado === 'Válido') marca.estado = 'Por Validar';
                    });
                }
                console.log(`Día ${fecha} DESBLOQUEADO:`, this.todosLosRegistros[fecha]);
            } else {
                // CONFIRMAR: Añadimos a la lista
                this.fechasConfirmadas.push(fecha);
                
                // Cambiamos a 'Válido' todos los registros adentro del modal
                if (this.todosLosRegistros[fecha]) {
                    this.todosLosRegistros[fecha].forEach(marca => {
                        if (marca.estado !== 'Descartado') marca.estado = 'Válido';
                    });
                }
                console.log(`Día ${fecha} CONFIRMADO:`, this.todosLosRegistros[fecha]);
            }
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
                id_registro: null, 
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

            // Regla 1: La cantidad de marcas activas debe ser estrictamente 4 o 6.
            // Se permite 0 por si el administrador decide descartar todo el dia.
            if (marcasActivas > 0 && marcasActivas !== 4 && marcasActivas !== 6) {
                this.notificar(`Inconsistencia: El dia debe tener exactamente 4 o 6 marcas. Actualmente existen ${marcasActivas} activas.`, "warning");
                return; 
            }

            // Regla 2: Obligar a revisar todos los estados.
            // No se permite guardar si existen marcas activas con estado "Por Validar" o "Inconsistente".
            const marcasSinRevisar = marcasActivasLista.filter(m => 
                m.estado === 'Por Validar' || m.estado === 'Inconsistente'
            );

            if (marcasSinRevisar.length > 0) {
                this.notificar("Aun existen registros 'Por Validar' o 'Inconsistentes'. Revise y asigne un estado valido a cada marcacion.", "warning");
                return; 
            }

            // Regla 3: No permitir horas duplicadas exactas.
            const horas = marcasActivasLista.map(m => m.hora);
            if (horas.length !== new Set(horas).size) {
                this.notificar("Error: Existen dos o mas marcaciones con exactamente la misma hora. Por favor, corrija las horas duplicadas.", "error");
                return; 
            }

            // Regla 4: No permitir tipos de marcas repetidos (ej. dos "Entrada" activas).
            let tiposActivos = new Set();
            for (let marca of marcasActivasLista) {
                if (tiposActivos.has(marca.tipo)) {
                    this.notificar(`Error: Tiene mas de un registro de "${marca.tipo}" activo. Debe descartar uno o cambiar el tipo.`, "error");
                    return; 
                }
                tiposActivos.add(marca.tipo);
            }

            // Paso 5: Cierre y guardado en memoria
            // A. Ordenar las marcas cronologicamente
            this.modalMarcaciones.sort((a, b) => a.hora.localeCompare(b.hora));

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
            // PASO 6: Envío Final al Backend (AÚN POR IMPLEMENTAR EN FLASK)
            if (!this.hayCambiosGuardados) return;

            // Preparar los datos (JSON) para enviar por Fetch
            let payload = {
                id_funcionario: this.datosUsuario ? this.datosUsuario.nombres : null,
                fechas_modificadas: {}
            };

            // Solo enviamos los días que sufrieron modificaciones para no saturar la red
            this.fechasModificadas.forEach(fecha => {
                payload.fechas_modificadas[fecha] = this.todosLosRegistros[fecha];
            });

            console.log("Payload que se enviará al Backend:", payload);
            this.notificar("Simulación: Datos listos para enviar al backend. Revisa la consola.", "info");
            
            // FUTURO: Aquí va el fetch('url_guardar', { method: 'POST', body: JSON.stringify(payload) })
        }
    }));
});