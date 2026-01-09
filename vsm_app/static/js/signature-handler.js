/* * Script para manejar la interfaz de usuario, el canvas y la lógica de dibujo.
 * Requiere wacomstu540.js cargado previamente.
 */

document.addEventListener('DOMContentLoaded', () => {
    const modalFirma = document.getElementById('modalFirma');
    const abrirFirmaBtn = document.getElementById('abrirFirmaBtn');
    const cerrarModalFirma = document.getElementById('cerrarModalFirma');
    const cancelarFirmaBtn = document.getElementById('cancelarFirmaBtn');
    const guardarFirmaBtn = document.getElementById('guardarFirmaBtn');
    const signatureCanvas = document.getElementById('signatureCanvas');
    const form = document.getElementById("formEntrega");
    const ctx = signatureCanvas.getContext('2d');
    

    // Inicializa la librería del driver
    let lastX = null;
    let lastY = null;
    let isSigning = false;

    // --- Configuración del Canvas de Firma ---

    const setupCanvas = () => {
        const wacomDriver = new wacomstu540();
        // Asegura que la pluma tenga un color visible (ej: azul)
        wacomDriver.setPenColorAndWidth('#000000ff', 3);
        // Limpia el canvas en la pantalla y en la tableta Wacom
        ctx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
        wacomDriver.clearScreen();

        wacomDriver.setInking(true);
        
        isSigning = false;
        lastX = null;
        lastY = null;
    };

    // --- Manejo de la Conexión y Dibujo ---

    const handlePenData = (packet) => {
        const penDown = packet.sw;

        const x = packet.cx; 
        const y = packet.cy; 

        // AÑADE ESTO:
        if (penDown) {
            console.log(`[DATA] Lápiz tocando. Coords: ${packet.cx}, ${packet.cy}`);
        }

        if (penDown) {
            if (isSigning && lastX !== null && lastY !== null) {
                const drawX = x; 
                const drawY = y;
                
                ctx.beginPath();
                ctx.moveTo(lastX, lastY);
                ctx.lineTo(drawX, drawY);
                ctx.strokeStyle = '#000000ff'; // Color de la pluma
                ctx.lineWidth = 3;               // Grosor del trazo
                ctx.stroke();
                ctx.closePath();
                
                lastX = drawX;
                lastY = drawY;

            } else {
                isSigning = true;
                lastX = x;
                lastY = y;
            }
        } else {
            isSigning = false;
            lastX = null;
            lastY = null;
        }
    };

    function mostrarLoader() {
        document.getElementById("loaderOverlay").classList.remove("hidden");
    }

    function ocultarLoader() {
        document.getElementById("loaderOverlay").classList.add("hidden");
    }
    
    // --- LÓGICA CLAVE PARA GUARDAR FIRMA Y CONFIRMAR ---

    guardarFirmaBtn.addEventListener('click', async () => {

        const signatureImage = signatureCanvas.toDataURL('image/png');
        
        const formData = new FormData(form);
        
        formData.append('firma_base64', signatureImage);

        formData.append('tipo_entrega', 'EPP'); 

        mostrarLoader();
        
        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" } 
            });

            const data = await response.json();
            ocultarLoader();
            
            if (response.ok && data.success) {
                console.log('✅ Firma y confirmación EPP exitosa.');
                showToast("Entrega guardada y confirmada correctamente ✅", "success");
                
                document.getElementById("abrirFirmaBtn").disabled = true;
                document.getElementById("abrirFirmaBtn").hidden = true;
                
            } else {
                console.error('❌ Error del servidor:', data);
                const mensajeError = data.error || "Error al guardar entrega ❌";
                showToast(`Error al guardar entrega ❌\n${mensajeError}`, "error");
            }

        } catch (error) {
            console.error('❌ Error en fetch:', error);
            ocultarLoader();
            showToast("Error de conexión con el servidor ❌", "error");
        } finally {
            setupCanvas(); 
            closeModal();
        }
    });
    

    // --- Eventos de UI y Conexión ---

    // 1. Abrir Modal y Conectar Wacom
    abrirFirmaBtn.addEventListener('click', async () => {
        modalFirma.classList.remove('hidden');
        const wacomDriver = new wacomstu540();
        try {
            // Intentar conectar con la Wacom (se abrirá el selector HID)
            const connected = await wacomDriver.connect();
            
            if (connected) {
                console.log('✅ Wacom STU-540 conectada y configurada.');
                
                // 🚨 NUEVA PRUEBA: Esperar 100ms para asegurar que el driver terminó de leer info.
                await new Promise(resolve => setTimeout(resolve, 100)); 
                
                // Habilitar Modo de Escritura (Modo 1)
                await wacomDriver.setWritingMode(1); 
                
                // Asignar el callback de dibujo al driver
                wacomDriver.onPenData(handlePenData);
                
                // Inicializar el canvas 
                setupCanvas();

            } else {
                console.warn('⚠️ No se pudo conectar la Wacom. Asegúrate de seleccionarla.');
                // Opcional: Mostrar mensaje de error al usuario
            }

        } catch (error) {
            console.error('❌ Error al conectar o abrir la Wacom:', error);
            // Si la conexión falla (ej: permisos denegados), cerrar el modal
            modalFirma.classList.add('hidden');
        }
    });

    // 2. Cerrar Modal (Cancelar)
    const closeModal = () => {
        modalFirma.classList.add('hidden');
        // Opcional: Desconectar el dispositivo si el driver lo permite, 
        // aunque WebHID suele mantener la conexión hasta que la página se cierra.
    };

    cerrarModalFirma.addEventListener('click', closeModal);
    cancelarFirmaBtn.addEventListener('click', closeModal);

    // 3. Guardar Firma
    guardarFirmaBtn.addEventListener('click', () => {

        const signatureImage = signatureCanvas.toDataURL('image/png');
        
        console.log('Firma capturada (Base64):', signatureImage.substring(0, 50) + '...');
        
        // Limpiar y cerrar
        setupCanvas(); 
        closeModal();
    });
});