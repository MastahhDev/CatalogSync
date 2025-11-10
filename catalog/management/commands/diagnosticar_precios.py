# catalog/management/commands/diagnosticar_precios.py
from django.core.management.base import BaseCommand
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Diagnostica juegos con precios en 0 o NULL'

    def handle(self, *args, **options):
        # Juegos secundarios sin precio
        secundarios_sin_precio = Juego.objects.filter(
            es_solo_secundario=True
        ).filter(
            precio_secundario__isnull=True
        ) | Juego.objects.filter(
            es_solo_secundario=True,
            precio_secundario=0
        )
        
        self.stdout.write(self.style.WARNING('\n🔍 JUEGOS SECUNDARIOS SIN PRECIO:'))
        for juego in secundarios_sin_precio:
            self.stdout.write(f"  - {juego.nombre}")
            self.stdout.write(f"    precio: {juego.precio}")
            self.stdout.write(f"    precio_secundario: {juego.precio_secundario}")
            self.stdout.write(f"    recargo: {juego.recargo}")
            self.stdout.write(f"    recargo_secundario: {juego.recargo_secundario}")
            self.stdout.write(f"    es_solo_secundario: {juego.es_solo_secundario}")
            self.stdout.write(f"    disponible: {juego.disponible}\n")
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal encontrados: {secundarios_sin_precio.count()}'))