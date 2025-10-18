# catalog/management/commands/cargar_maestros.py
import csv
import os
import re
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

    def determinar_consola(self, nombre):
        """Determina la consola basándose en el nombre del juego"""
        nombre_lower = nombre.lower()
        
        if 'ps5' in nombre_lower or 'playstation 5' in nombre_lower:
            return 'ps5'
        elif 'ps4' in nombre_lower or 'playstation 4' in nombre_lower:
            return 'ps4'
        else:
            # Por defecto PS4 si no se puede determinar
            return 'ps4'

    def buscar_imagen(self, nombre_juego):
        """Busca la imagen correspondiente al juego"""
        nombre = nombre_juego.lower()
        
        # Determinar consola para la imagen
        if 'ps5' in nombre:
            consola = 'ps5'
        else:
            consola = 'ps4'
        
        # Quitar consola del nombre para búsqueda
        nombre = nombre.replace(' ps4', '').replace(' ps5', '').replace('(ps4)', '').replace('(ps5)', '').strip()
        
        # Limpiar caracteres
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre_archivo = nombre.replace(' ', '_')
        
        # Probar diferentes extensiones y formatos
        posibles_nombres = [
            f'{nombre_archivo}_{consola}.jpg',
            f'{nombre_archivo}_{consola}.png',
            f'{nombre_archivo}.jpg',
            f'{nombre_archivo}.png',
        ]
        
        for nombre_img in posibles_nombres:
            imagen_path = f'img/{nombre_img}'
            imagen_completa = os.path.join(settings.BASE_DIR, 'static', imagen_path)
            if os.path.exists(imagen_completa):
                return imagen_path
        
        return 'img/default.png'

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
                
                self.stdout.write(f"Columnas encontradas: {csv_reader.fieldnames}")
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre = row.get('nombre', '').strip()
                        if not nombre:
                            continue
                        
                        descripcion = row.get('descripcion', '').strip()
                        genero = row.get('genero', '').strip()
                        
                        # ✅ DETERMINAR CONSOLA AUTOMÁTICAMENTE
                        consola = self.determinar_consola(nombre)
                        
                        # Destacado
                        destacado_valor = row.get('destacado', '').strip().lower()
                        destacado = destacado_valor in ['1', 'si', 'yes', 'true', 'destacado']
                        
                        # ✅ BUSCAR IMAGEN MEJORADA
                        imagen_path = self.buscar_imagen(nombre)
                        
                        # Obtener o crear el juego
                        juego, created = Juego.objects.get_or_create(
                            nombre=nombre,
                            defaults={
                                'precio': 0,
                                'recargo': 0,
                                'consola': consola,  # ← CONSOLA CORRECTA
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
                            self.stdout.write(self.style.SUCCESS(f'NUEVO [{consola.upper()}]: {nombre}'))
                        else:
                            actualizados += 1
                            self.stdout.write(f'Actualizado [{consola.upper()}]: {nombre}')
                        
                    except Exception as e:
                        errores.append(f'Linea {linea_num}: {str(e)}')
                        self.stdout.write(self.style.ERROR(f'Error linea {linea_num}: {str(e)}'))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al leer archivo: {str(e)}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'{actualizados} juegos actualizados'))
        self.stdout.write(self.style.SUCCESS(f'{creados} juegos nuevos'))
        
        # Mostrar estadísticas por consola
        ps4_count = Juego.objects.filter(consola='ps4').count()
        ps5_count = Juego.objects.filter(consola='ps5').count()
        self.stdout.write(self.style.SUCCESS(f'PS4 en BD: {ps4_count}'))
        self.stdout.write(self.style.SUCCESS(f'PS5 en BD: {ps5_count}'))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\n{len(errores)} errores'))
            for error in errores[:5]:
                self.stdout.write(self.style.ERROR(f'  - {error}'))