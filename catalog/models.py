# catalog/models.py
from django.db import models
from django.utils.text import slugify
from decimal import Decimal

class Juego(models.Model):
    CONSOLAS = [
        ('ps4', 'PlayStation 4'),
        ('ps5', 'PlayStation 5'),
    ]
    
    nombre = models.CharField(max_length=200)
    consola = models.CharField(max_length=10, choices=CONSOLAS)
    destacado = models.BooleanField(default=False)
    descripcion = models.TextField(
        blank=True, 
        null=True,
        help_text="Descripción del juego"
    )
    
    # PRECIOS PRIMARIOS
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # PRECIOS SECUNDARIOS
    precio_secundario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Precio del proveedor secundario"
    )
    recargo_secundario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Recargo del precio secundario"
    )
    tiene_secundario = models.BooleanField(
        default=False,
        help_text="Indica si este juego tiene precio secundario disponible"
    )
    es_solo_secundario = models.BooleanField(
        default=False,
        help_text="Indica si este juego solo existe como secundario (sin primario)"
    )
    
    # CAMPOS EXISTENTES
    imagen = models.CharField(max_length=200, default='img/default.jpg')
    disponible = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nombre']
        verbose_name = 'Juego'
        verbose_name_plural = 'Juegos'
    
    def __str__(self):
        if self.tiene_secundario:
            return f"{self.nombre} ({self.consola.upper()}) - Primario: ${self.precio} | Secundario: ${self.precio_secundario}"
        return f"{self.nombre} ({self.consola.upper()}) - ${self.precio}"
    
    # ⭐ MÉTODO PARA GENERAR SLUG
    def get_slug(self):
        """
        Genera un slug único basado en el ID y el nombre del juego.
        Formato: {id}-{nombre-slugificado}
        Ejemplo: 10-a-way-out-ps4
        """
        from django.utils.text import slugify
        nombre_limpio = self.nombre.lower()
        # Remover "PS4" o "PS5" del nombre para el slug
        nombre_limpio = nombre_limpio.replace(' ps4', '').replace(' ps5', '').strip()
        nombre_slug = slugify(nombre_limpio)
        return f"{self.id}-{nombre_slug}"
    
    def get_precio_menor(self):
        """Retorna el precio más bajo disponible"""
        if self.tiene_secundario and self.precio_secundario:
            return min(self.precio, self.precio_secundario)
        return self.precio
    
    def get_precio_mayor(self):
        """Retorna el precio más alto disponible"""
        if self.tiene_secundario and self.precio_secundario:
            return max(self.precio, self.precio_secundario)
        return self.precio
    
class Utilidades(models.Model):
    class Meta:
        managed = False
        verbose_name = "Utilidad"
        verbose_name_plural = "Utilidades"

    def __str__(self):
        return "Utilidades del sistema"

from django.db import models
from django.utils.text import slugify

class ResenaCliente(models.Model):
    cliente = models.CharField(max_length=100, help_text="Usuario de Instagram")
    juego = models.CharField(max_length=200)
    reseña = models.TextField()
    imagen = models.CharField(max_length=255, blank=True, null=True, 
                             help_text="Ruta de la imagen (se busca automáticamente)")
    activo = models.BooleanField(default=True)
    fecha = models.DateField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Reseña de Cliente"
        verbose_name_plural = "Reseñas de Clientes"
    
    def __str__(self):
        return f"@{self.cliente} - {self.juego}"
    
    def get_nombre_archivo_imagen(self):
        """Devuelve el nombre del archivo de imagen"""
        if self.imagen:
            return self.imagen
        # Fallback: buscar por nombre de usuario
        nombre_limpio = slugify(self.cliente)
        return f"img/{nombre_limpio}.jpg"
    
    def existe_imagen(self):
        """Verifica si existe la imagen del cliente"""
        import os
        from django.conf import settings
        ruta_imagen = os.path.join(settings.STATICFILES_DIRS[0], self.get_nombre_archivo_imagen())
        return os.path.exists(ruta_imagen)