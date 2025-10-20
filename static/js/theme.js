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
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
});

// Inicializar cuando el DOM esté listo
window.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
});

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        this.applyTheme(e.matches ? 'dark' : 'light');
    }
});

