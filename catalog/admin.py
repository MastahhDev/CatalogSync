# catalog/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Juego
from .forms import JuegoAdminForm

@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    form = JuegoAdminForm
    list_display = [
        'nombre',
        'consola',
        'mostrar_precio',
        'mostrar_precio_secundario',
        'disponible',
        'tiene_secundario',
        'es_solo_secundario',
        'fecha_actualizacion'
    ]
    
    list_filter = [
        'consola',
        'disponible',
        'tiene_secundario',
        'es_solo_secundario',
    ]
    
    search_fields = ['nombre']
    
    list_editable = ['disponible']
    
    readonly_fields = [
        'fecha_creacion',
        'fecha_actualizacion',
        'mostrar_imagen_preview'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'consola', 'imagen', 'nueva_portada', 'mostrar_imagen_preview', 'disponible')
        }),
        ('Precios Primarios', {
            'fields': ('precio', 'recargo'),
            'classes': ('collapse',)
        }),
        ('Precios Secundarios', {
            'fields': (
                'precio_secundario',
                'recargo_secundario',
                'tiene_secundario',
                'es_solo_secundario'
            ),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def mostrar_precio(self, obj):
        """Muestra el precio primario con formato"""
        if obj.precio:
            return format_html(
                '<span style="color: green; font-weight: bold;">${}</span> / <span style="color: blue;">${}</span>',
                f'{obj.precio:,.0f}',
                f'{obj.recargo:,.0f}'
            )
        return '-'
    mostrar_precio.short_description = '💰 Precio Primario (Base/Recargo)'
    
    def mostrar_precio_secundario(self, obj):
        """Muestra el precio secundario si existe"""
        if obj.tiene_secundario and obj.precio_secundario:
            # Determinar cuál es más barato
            if obj.precio_secundario < obj.precio:
                color = '#FFD700'  # Dorado si es más barato
                icono = '⭐'
            else:
                color = '#2196F3'  # Azul normal
                icono = '🔵'
            
            return format_html(
                '<span style="background: {}; padding: 3px 8px; border-radius: 3px;">{} ${} / ${}</span>',
                color,
                icono,
                f'{obj.precio_secundario:,.0f}',
                f'{obj.recargo_secundario:,.0f}'
            )
        return format_html('<span style="color: #999;">-</span>')
    mostrar_precio_secundario.short_description = '🔵 Precio Secundario'
    
    def mostrar_imagen_preview(self, obj):
        """Muestra preview de la imagen"""
        if obj.imagen and obj.imagen != 'img/default.jpg':
            return format_html(
                '<img src="/static/{}" style="max-height: 200px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.imagen
            )
        return format_html('<span style="color: #999;">Sin imagen</span>')
    mostrar_imagen_preview.short_description = '🖼️ Preview'
    
    # Acciones personalizadas
    actions = ['marcar_disponible', 'marcar_no_disponible', 'eliminar_precio_secundario']
    
    def marcar_disponible(self, request, queryset):
        """Marca los juegos seleccionados como disponibles"""
        updated = queryset.update(disponible=True)
        self.message_user(request, f'{updated} juego(s) marcado(s) como disponible(s).')
    marcar_disponible.short_description = '✅ Marcar como disponible'
    
    def marcar_no_disponible(self, request, queryset):
        """Marca los juegos seleccionados como no disponibles"""
        updated = queryset.update(disponible=False)
        self.message_user(request, f'{updated} juego(s) marcado(s) como NO disponible(s).')
    marcar_no_disponible.short_description = '❌ Marcar como NO disponible'
    
    def eliminar_precio_secundario(self, request, queryset):
        """Elimina el precio secundario de los juegos seleccionados"""
        updated = queryset.update(
            precio_secundario=None,
            recargo_secundario=None,
            tiene_secundario=False
        )
        self.message_user(request, f'Precio secundario eliminado de {updated} juego(s).')
    eliminar_precio_secundario.short_description = '🔵 Eliminar precio secundario'