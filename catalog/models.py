# catalog/models.py
from django.db import models
from django.utils.text import slugify

class Juego(models.Model):
    CONSOLAS = [
        ('ps4', 'PlayStation 4'),
        ('ps5', 'PlayStation 5'),
    ]
    
    nombre = models.CharField(max_length=200, unique=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    consola = models.CharField(max_length=10, choices=CONSOLAS)
    disponible = models.BooleanField(default=False)
    destacado = models.BooleanField(default=False)
    imagen = models.CharField(max_length=500, blank=True)
    descripcion = models.TextField(blank=True, null=True)
    genero = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Juego'
        verbose_name_plural = 'Juegos'
        ordering = ['-destacado', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.consola}"
    
    def get_slug(self):
        # Usa slugify de Django que maneja mejor los caracteres especiales
        return slugify(self.nombre)
    
    