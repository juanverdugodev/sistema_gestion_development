let dragCounter = 0;
    
window.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dragCounter++;
    window.dispatchEvent(new CustomEvent('global-drag-enter'));
});

window.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter === 0) {
        window.dispatchEvent(new CustomEvent('global-drag-leave'));
    }
});

window.addEventListener('dragover', (e) => e.preventDefault());

window.addEventListener('drop', (e) => {
    e.preventDefault();
    dragCounter = 0;
    window.dispatchEvent(new CustomEvent('global-drag-leave'));
    
    if (e.dataTransfer.files.length > 0) {
        window.dispatchEvent(new CustomEvent('process-files', { detail: e.dataTransfer.files }));
    }
});

window.uploadHandler = function() {
    return {
        showModal: false,       
        excelSummary: null,      
        tempFile: null,         
        urls: {}, // Objeto para guardar las rutas de Flask

        init() {
            // Capturamos las rutas pasadas desde HTML por atributos data-*
            this.urls = {
                process: this.$root.dataset.urlProcess,
                confirm: this.$root.dataset.urlConfirm,
                cancel: this.$root.dataset.urlCancel
            };

            window.addEventListener('process-files', (e) => {
                this.processFiles(e.detail);
            });
        },

        handleFileSelect(event) {
            const files = event.target.files;
            this.processFiles(files);
        },

        processFiles(files) {
            if (files.length === 0) return;
            const file = files[0];
            
            const validExtensions = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'];
            if (!validExtensions.includes(file.type) && !file.name.toLowerCase().endsWith('.xlsx')) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: "Error: El archivo debe ser obligatoriamente un documento Excel (.xlsx).", type: "error" }
                }));
                return;
            }

            window.dispatchEvent(new CustomEvent('show-loading', {
                detail: { message: "Pre-procesando Excel y validando columnas..." }
            }));

            const formData = new FormData();
            formData.append('file', file);

            // Usamos la URL capturada dinámicamente
            fetch(this.urls.process, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json().then(data => ({ status: response.status, body: data })))
            .then(res => {
                window.dispatchEvent(new CustomEvent('hide-loading'));
                if (res.status === 200) {
                    this.excelSummary = res.body.resumen;
                    this.tempFile = res.body.archivo_temp;
                    this.showModal = true; 
                } else {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: res.body.error || "Error al leer el archivo.", type: "error" }
                    }));
                }
            })
            .catch(error => {
                console.error("Error:", error);
                window.dispatchEvent(new CustomEvent('hide-loading'));
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: "Error crítico de conexión.", type: "error" }
                }));
            })
            .finally(() => {
                document.getElementById('fileInput').value = '';
            });
        },

        confirmarGuardado() {
            window.dispatchEvent(new CustomEvent('show-loading', {
                detail: { message: "Procesando registros. Esto puede tomar un minuto..." }
            }));

            // Usamos la URL de confirmación
            fetch(this.urls.confirm, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    archivo_temp: this.tempFile
                })
            })
            .then(response => response.json().then(data => ({ status: response.status, body: data })))
            .then(res => {
                window.dispatchEvent(new CustomEvent('hide-loading'));
                if (res.status === 200) {
                    // El mensaje de éxito ya viene estructurado y completo desde el backend
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: res.body.mensaje, type: "success" }
                    }));
                    this.showModal = false;
                    this.excelSummary = null;
                    this.tempFile = null;
                } else {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: res.body.error || "Error al procesar los datos.", type: "error" }
                    }));
                }
            })
            .catch(error => {
                window.dispatchEvent(new CustomEvent('hide-loading'));
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: "Error crítico durante la importación.", type: "error" }
                }));
            });
        },

        cancelarGuardado() {
            this.showModal = false;
            if (this.tempFile) {
                // Usamos la URL de cancelación
                fetch(this.urls.cancel, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: this.tempFile })
                });
            }
            this.excelSummary = null;
            this.tempFile = null;
            window.dispatchEvent(new CustomEvent('notify', {
                detail: { message: "Importación cancelada.", type: "warning" }
            }));
        }
    }
}