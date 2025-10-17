# catalog/management/commands/actualizar_ps4.py
import csv
import os
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Actualiza stock de PS4 desde CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='stock_ps4.csv',
            help='CSV con juegos de PS4'
        )
        parser.add_argument(
            '--columna-nombre',
            type=str,
            default='JUEGOS',
            help='Nombre de la columna con el nombre del juego'
        )
        parser.add_argument(
            '--columna-precio',
            type=str,
            default='PRECIO',
            help='Nombre de la columna con el precio'
        )

    def buscar_juego_similar(self, nombre_limpio):
        """Busca juegos en la base de datos que coincidan aproximadamente"""
        # Primero intenta búsqueda exacta sin "PS4"
        nombre_sin_ps4 = nombre_limpio.replace(' PS4', '').strip()
        
        # Buscar coincidencias exactas
        juegos_exactos = Juego.objects.filter(
            nombre__iexact=nombre_limpio,
            consola='ps4'
        )
        if juegos_exactos.exists():
            return juegos_exactos.first()
        
        # Buscar por nombre sin "PS4"
        juegos_sin_ps4 = Juego.objects.filter(
            nombre__icontains=nombre_sin_ps4,
            consola='ps4'
        )
        if juegos_sin_ps4.exists():
            return juegos_sin_ps4.first()
        
        # Buscar por palabras clave (las primeras 3-4 palabras)
        palabras_clave = nombre_sin_ps4.split()[:4]
        query = None
        for palabra in palabras_clave:
            if len(palabra) > 3:  # Solo palabras significativas
                if query is None:
                    query = models.Q(nombre__icontains=palabra)
                else:
                    query |= models.Q(nombre__icontains=palabra)
        
        if query:
            juegos_similares = Juego.objects.filter(query, consola='ps4')
            if juegos_similares.exists():
                return juegos_similares.first()
        
        return None

    def limpiar_nombre(self, nombre):
        """Limpia el nombre para búsqueda"""
        if not nombre:
            return ""
            
        # Quitar emojis y caracteres especiales
        nombre = re.sub(r'[^\x00-\x7F]+', '', nombre)
        
        # Quitar símbolos especiales
        nombre = nombre.replace('®', '').replace('™', '').replace('©', '')
        nombre = nombre.replace(':', '').replace('#', '').replace('-', ' ')
        
        # Quitar el precio del nombre si está
        nombre = re.sub(r'\$\s*[\d.,]+', '', nombre)
        
        # Quitar caracteres especiales al inicio
        nombre = re.sub(r'^[\'\"\#\-\s]+', '', nombre)
        
        # Quitar múltiples espacios
        nombre = re.sub(r'\s+', ' ', nombre)
        
        # Quitar espacios al inicio y final
        return nombre.strip()

    def limpiar_precio(self, precio_str):
        """Convierte string con precio a Decimal"""
        if not precio_str or precio_str.strip() == '':
            return Decimal('0.0')
        
        precio_str = str(precio_str).replace('$', '').replace(' ', '').strip()
        
        if ',' in precio_str and '.' in precio_str:
            precio_str = precio_str.replace('.', '').replace(',', '.')
        elif ',' in precio_str:
            precio_str = precio_str.replace(',', '.')
        
        precio_str = re.sub(r'[^\d.]', '', precio_str)
        
        try:
            return Decimal(precio_str)
        except:
            return Decimal('0.0')

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        col_precio = options['columna_precio']
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontro {csv_path}'))
            return
        
        # NO marcar todos como no disponibles al inicio
        # En su lugar, recolectar los IDs que SÍ están en stock
        juegos_en_stock_ids = []
        actualizados = 0
        creados = 0
        errores = []
        no_encontrados = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                self.stdout.write(f"Columnas encontradas: {csv_reader.fieldnames}")
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_nombre}"'))
                    return
                
                if col_precio not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_precio}"'))
                    return
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre_sucio = row.get(col_nombre, '').strip()
                        if not nombre_sucio:
                            continue
                        
                        nombre_limpio = self.limpiar_nombre(nombre_sucio)
                        
                        if not nombre_limpio or len(nombre_limpio) < 3:
                            continue
                        
                        # Agregar PS4 al nombre si no lo tiene
                        if not nombre_limpio.upper().endswith('PS4'):
                            nombre_busqueda = f"{nombre_limpio} PS4"
                        else:
                            nombre_busqueda = nombre_limpio
                        
                        # Buscar juego en la base de datos
                        juego = self.buscar_juego_similar(nombre_busqueda)
                        
                        if not juego:
                            no_encontrados.append(nombre_busqueda)
                            self.stdout.write(self.style.WARNING(f'NO ENCONTRADO: {nombre_busqueda}'))
                            continue
                        
                        # Obtener y limpiar precio
                        precio_str = row.get(col_precio, '').strip()
                        precio = self.limpiar_precio(precio_str)
                        
                        # Actualizar el juego encontrado
                        juego.precio = precio
                        juego.recargo = Decimal('0.0')
                        juego.disponible = True
                        juego.save()
                        
                        juegos_en_stock_ids.append(juego.id)
                        actualizados += 1
                        self.stdout.write(self.style.SUCCESS(f'ACTUALIZADO: {juego.nombre} - ${precio}'))
                        
                    except Exception as e:
                        error_msg = f'Linea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        # Ahora marcar como no disponibles los PS4 que NO están en el stock
        if juegos_en_stock_ids:
            juegos_a_desactivar = Juego.objects.filter(consola='ps4').exclude(id__in=juegos_en_stock_ids)
            desactivados_count = juegos_a_desactivar.update(disponible=False)
        else:
            desactivados_count = 0
        
        # Resultados
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'ACTUALIZADOS: {actualizados}'))
        self.stdout.write(self.style.SUCCESS(f'DESACTIVADOS: {desactivados_count}'))
        self.stdout.write(self.style.WARNING(f'NO ENCONTRADOS: {len(no_encontrados)}'))
        
        if no_encontrados:
            self.stdout.write(self.style.WARNING("\nJuegos no encontrados en BD:"))
            for nombre in no_encontrados[:10]:
                self.stdout.write(f"  - {nombre}")