// static/js/theme.js

class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 
           (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

        this.init();
    }
    
    init() {
        this.applyTheme(this.theme);
        this.addEventListeners();
        this.updateToggleButton(this.theme);
        
        // Observar cambios de tema para actualizar el carrito
        this.setupThemeObserver();
        
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            // Solo cambiar automáticamente si no hay una preferencia guardada
            if (!localStorage.getItem('theme')) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.updateToggleButton(theme);
        
        // Actualizar el carrito si está abierto
        this.actualizarCarritoTema();
    }
    
    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.theme);
    }
    
    updateToggleButton(theme) {
        const iconSpan = document.getElementById('theme-icon');
        const textSpan = document.getElementById('theme-text');

        if (iconSpan && textSpan) {
            const icon = theme === 'light' ? '☀️' : '🌙';
            const text = theme === 'light' ? 'Modo Claro' : 'Modo Oscuro';
            iconSpan.textContent = icon;
            textSpan.textContent = text;
        }
    }
    
    addEventListeners() {
        const toggleButton = document.getElementById('theme-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', () => this.toggleTheme());
        }
    }
    
    setupThemeObserver() {
        // Observar cambios en el atributo data-theme para actualizar el carrito
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    setTimeout(() => this.actualizarCarritoTema(), 50);
                }
            });
        });

        observer.observe(document.documentElement, {
            attributes: true
        });
    }
    
    actualizarCarritoTema() {
        const carritoPopup = document.getElementById('carrito-popup');
        if (carritoPopup && carritoPopup.classList.contains('show')) {
            // Recargar contenido del carrito manteniéndolo abierto
            this.recargarCarrito();
        }
    }
    
    recargarCarrito() {
        const carritoToggle = document.getElementById('carrito-toggle');
        if (carritoToggle && window.htmx) {
            // Guardar estado actual del carrito
            const isOpen = document.getElementById('carrito-popup').classList.contains('show');
            
            // Recargar el contenido
            htmx.trigger(carritoToggle, 'click');
            
            // Si estaba abierto, mantenerlo abierto después de recargar
            if (isOpen) {
                setTimeout(() => {
                    htmx.trigger(carritoToggle, 'click');
                }, 100);
            }
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});