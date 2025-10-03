from django.db import models

class Juego(models.Model):
    CONSOLAS = [
        ('ps4', 'PlayStation 4'),
        ('ps5', 'PlayStation 5'),
    ]
    
    # Campos existentes
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    consola = models.CharField(max_length=10, choices=CONSOLAS)
    destacado = models.BooleanField(default=False)
    imagen = models.CharField(max_length=500, blank=True)
    
    # Nuevos campos para detalle
    descripcion = models.TextField(blank=True, null=True)
    genero = models.CharField(max_length=100, blank=True, null=True)
    stock = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Juego'
        verbose_name_plural = 'Juegos'
        ordering = ['-destacado', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.consola}"
    
    def get_slug(self):
        return self.nombre.lower().replace(' ', '-')