# catalog/management/commands/verificar_imagenes.py
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Verifica qué juegos tienen imágenes'

    def handle(self, *args, **options):
        juegos_sin_imagen = []
        juegos_con_imagen = []
        
        for juego in Juego.objects.all():
            if juego.imagen and juego.imagen != "img/default.jpg":
                img_path = os.path.join(settings.BASE_DIR, 'static', juego.imagen)
                if os.path.exists(img_path):
                    juegos_con_imagen.append(juego.nombre)
                else:
                    juegos_sin_imagen.append(juego.nombre)
            else:
                juegos_sin_imagen.append(juego.nombre)
        
        self.stdout.write(self.style.SUCCESS(f"Juegos CON imagen: {len(juegos_con_imagen)}"))
        self.stdout.write(self.style.ERROR(f"Juegos SIN imagen: {len(juegos_sin_imagen)}"))
        
        if juegos_sin_imagen:
            self.stdout.write("\nJuegos sin imagen:")
            for nombre in juegos_sin_imagen[:20]:
                self.stdout.write(f"  - {nombre}")