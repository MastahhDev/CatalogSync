import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Importa juegos desde el archivo CSV'

    def handle(self, *args, **kwargs):
        csv_path = os.path.join(settings.BASE_DIR, 'juegos.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontró {csv_path}'))
            return
        
        # Borrar juegos existentes (opcional, puedes comentar esta línea si prefieres actualizar)
        Juego.objects.all().delete()
        self.stdout.write(self.style.WARNING('Juegos anteriores eliminados'))
        
        juegos_creados = 0
        
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            csv_reader.fieldnames = [name.strip().replace('\ufeff', '') for name in csv_reader.fieldnames]
            
            for row in csv_reader:
                row_limpio = {k.strip().replace('\ufeff', ''): v.strip() if v else '' for k, v in row.items()}
                
                nombre = row_limpio.get('nombre', '')
                if not nombre:
                    continue
                
                precio = float(row_limpio.get('precio', '0'))
                recargo = float(row_limpio.get('recargo', '0'))
                consola = row_limpio.get('consola', '').lower()
                destacado_valor = row_limpio.get('destacado', '').lower()
                destacado = destacado_valor in ['1', 'destacado', 'si', 'yes', 'true']
                
                # Buscar imagen
                nombre_archivo = nombre.lower().replace(' ', '_')
                imagen_path = f'img/{nombre_archivo}.png'
                imagen_completa = os.path.join(settings.BASE_DIR, 'static', imagen_path)
                
                if not os.path.exists(imagen_completa):
                    imagen_path = f'img/{nombre.lower()}.png'
                    imagen_completa = os.path.join(settings.BASE_DIR, 'static', imagen_path)
                
                if not os.path.exists(imagen_completa):
                    imagen_path = 'img/default.png'
                
                # Crear juego
                Juego.objects.create(
                    nombre=nombre,
                    precio=precio,
                    recargo=recargo,
                    consola=consola,
                    destacado=destacado,
                    imagen=imagen_path
                )
                
                juegos_creados += 1
                self.stdout.write(f'✓ {nombre}')
        
        self.stdout.write(self.style.SUCCESS(f'\n{juegos_creados} juegos importados correctamente'))