from django.contrib import admin
from .models import Juego

@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio', 'recargo', 'consola', 'destacado']
    list_filter = ['consola', 'destacado']
    search_fields = ['nombre']