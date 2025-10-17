# catalog/management/commands/cargar_maestros.py
import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Carga la info maestra de juegos (descripcion, genero, imagen)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='juegos.csv',
            help='CSV con info completa de juegos'
        )

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontro {csv_path}'))
            return
        
        actualizados = 0
        creados = 0
        errores = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                csv_reader = csv.DictReader(file)
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().lower() for name in csv_reader.fieldnames]
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre = row.get('nombre', '').strip()
                        if not nombre:
                            continue
                        
                        descripcion = row.get('descripcion', '').strip()
                        genero = row.get('genero', '').strip()
                        
                        # Destacado
                        destacado_valor = row.get('destacado', '').strip().lower()
                        destacado = destacado_valor in ['1', 'si', 'yes', 'true', 'destacado']
                        
                        # Buscar imagen
                        nombre_archivo = nombre.lower().replace(' ', '_')
                        imagen_path = f'img/{nombre_archivo}.png'
                        imagen_completa = os.path.join(settings.BASE_DIR, 'static', imagen_path)
                        
                        if not os.path.exists(imagen_completa):
                            imagen_path = 'img/default.png'
                        
                        # Obtener o crear el juego
                        juego, created = Juego.objects.get_or_create(
                            nombre=nombre,
                            defaults={
                                'precio': 0,
                                'recargo': 0,
                                'consola': 'ps4',
                                'disponible': False,
                            }
                        )
                        
                        # Actualizar SOLO los campos maestros
                        juego.descripcion = descripcion
                        juego.genero = genero
                        juego.imagen = imagen_path
                        juego.destacado = destacado
                        juego.save()
                        
                        if created:
                            creados += 1
                            self.stdout.write(self.style.SUCCESS(f'NUEVO: {nombre}'))
                        else:
                            actualizados += 1
                            self.stdout.write(f'Actualizado: {nombre}')
                        
                    except Exception as e:
                        errores.append(f'Linea {linea_num}: {str(e)}')
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al leer archivo: {str(e)}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'{actualizados} juegos actualizados'))
        self.stdout.write(self.style.SUCCESS(f'{creados} juegos nuevos'))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\n{len(errores)} errores'))
            for error in errores[:5]:
                self.stdout.write(self.style.ERROR(f'  - {error}'))