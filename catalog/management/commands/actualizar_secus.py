# catalog/management/commands/actualizar_secundarios.py
import csv
import os
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from catalog.models import Juego
from difflib import SequenceMatcher

class Command(BaseCommand):
    help = 'Actualiza juegos secundarios - agrega precio secundario si existe o crea nuevo juego'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='stock_secus.csv',
            help='CSV con juegos secundarios'
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
        parser.add_argument(
            '--consola',
            type=str,
            default='ps4',
            help='Consola (ps4 o ps5)'
        )

    def limpiar_nombre_avanzado(self, nombre):
        """Limpia el nombre quitando idiomas, ediciones específicas, etc."""
        if not nombre:
            return ""
            
        nombre = re.sub(r'[^\x00-\x7F]+', '', nombre)
        nombre = nombre.replace('®', '').replace('™', '').replace('©', '')
        nombre = nombre.replace(':', '').replace('#', '').replace('-', ' ')
        nombre = re.sub(r'\$\s*[\d.,]+', '', nombre)
        nombre = re.sub(r'^[\'\"\#\-\s]+', '', nombre)
        
        patrones_a_eliminar = [
            r'\bespañol\s+españa\b', r'\bespañol\s+latino\b', r'\binglés\b',
            r'\benglish\b', r'\bsubtitulado\b', r'\bsubtitulada\b',
            r'\bespañol\b', r'\bspanish\b',
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedición\s+deluxe\b', r'\bedición\s+gold\b',
            r'\bedición\s+estándar\b', r'\bedición\s+especial\b', r'\blatino\b',
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b',
        ]
        
        for patron in patrones_a_eliminar:
            nombre = re.sub(patron, '', nombre, flags=re.IGNORECASE)
        
        nombre = re.sub(r'\(\s*\)', '', nombre)
        nombre = re.sub(r'\[\s*\]', '', nombre)
        nombre = re.sub(r'\s+', ' ', nombre)
        nombre = nombre.strip()
        nombre = re.sub(r'[.,;\s]+$', '', nombre)
        
        return nombre

    def buscar_juego_similar(self, nombre_limpio, consola):
        """Busca juegos en la base de datos que coincidan aproximadamente"""
        nombre_sin_consola = nombre_limpio.replace(f' {consola.upper()}', '').replace(f' {consola}', '').strip()
        
        # Buscar coincidencias exactas
        juegos_exactos = Juego.objects.filter(
            nombre__iexact=nombre_limpio,
            consola=consola
        )
        if juegos_exactos.exists():
            return juegos_exactos.first()
        
        # Buscar por nombre sin consola
        juegos_sin_consola = Juego.objects.filter(
            nombre__icontains=nombre_sin_consola,
            consola=consola
        )
        if juegos_sin_consola.exists():
            return juegos_sin_consola.first()
        
        # Limpiar también el nombre para búsqueda más flexible
        nombre_muy_limpio = self.limpiar_nombre_avanzado(nombre_sin_consola)
        
        if nombre_muy_limpio != nombre_sin_consola:
            juegos_muy_limpios = Juego.objects.filter(
                nombre__icontains=nombre_muy_limpio,
                consola=consola
            )
            if juegos_muy_limpios.exists():
                return juegos_muy_limpios.first()
        
        # Buscar por palabras clave
        palabras_clave = nombre_muy_limpio.split()[:4]
        query = None
        for palabra in palabras_clave:
            if len(palabra) > 3:
                if query is None:
                    query = models.Q(nombre__icontains=palabra)
                else:
                    query |= models.Q(nombre__icontains=palabra)
        
        if query:
            juegos_similares = Juego.objects.filter(query, consola=consola)
            mejor_coincidencia = None
            mejor_ratio = 0.0

            for juego_candidato in juegos_similares:
                nombre_juego_limpio = self.limpiar_nombre_avanzado(juego_candidato.nombre)
                ratio = SequenceMatcher(None, nombre_muy_limpio.lower(), nombre_juego_limpio.lower()).ratio()

                if ratio > mejor_ratio:
                    mejor_ratio = ratio
                    mejor_coincidencia = juego_candidato

            if mejor_ratio > 0.85:
                return mejor_coincidencia
        
        return None

    def limpiar_precio(self, precio_str):
        """Convierte string con precio a Decimal - FORMATO ARGENTINO"""
        if not precio_str or precio_str.strip() == '':
            return Decimal('0.0')
        
        precio_str = str(precio_str).replace('$', '').replace(' ', '').strip()
        
        if ',' in precio_str:
            precio_str = precio_str.replace('.', '').replace(',', '.')
        else:
            precio_str = precio_str.replace('.', '')
        
        precio_str = re.sub(r'[^\d.]', '', precio_str)
        
        try:
            return Decimal(precio_str)
        except:
            return Decimal('0.0')
        
    def calcular_recargo(self, precio):
        """Calcula el recargo como 10% del precio"""
        if precio <= 0:
            return Decimal('0.0')
        
        recargo = precio + (precio * Decimal('0.10'))
        return recargo.quantize(Decimal('0.01'))

    def buscar_imagen(self, nombre_juego, consola):
        """Busca la imagen correspondiente al juego"""
        nombre = nombre_juego.lower()
        nombre = nombre.replace(f' {consola}', '').strip()
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre = nombre.replace(" ", "_")
        nombre_archivo = f"{nombre}_{consola}.jpg"
        
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        
        if os.path.exists(os.path.join(img_dir, nombre_archivo)):
            return f"img/{nombre_archivo}"
        
        archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        archivos_lower = [f.lower() for f in archivos_existentes]
        
        if nombre_archivo.lower() in archivos_lower:
            archivo_real = archivos_existentes[archivos_lower.index(nombre_archivo.lower())]
            return f"img/{archivo_real}"
        
        return "img/default.jpg"

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        col_precio = options['columna_precio']
        consola = options['consola'].lower()
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontró {csv_path}'))
            return
        
        actualizados_existentes = 0
        creados_nuevos = 0
        errores = []
        no_encontrados = []
        secundarios_ids = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                self.stdout.write(f"Columnas encontradas: {csv_reader.fieldnames}")
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontró la columna "{col_nombre}"'))
                    return
                
                if col_precio not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontró la columna "{col_precio}"'))
                    return
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre_sucio = row.get(col_nombre, '').strip()
                        if not nombre_sucio:
                            continue
                        
                        nombre_limpio = self.limpiar_nombre_avanzado(nombre_sucio)
                        
                        if not nombre_limpio or len(nombre_limpio) < 3:
                            continue
                        
                        # Agregar consola al nombre si no la tiene
                        if not nombre_limpio.upper().endswith(consola.upper()):
                            nombre_busqueda = f"{nombre_limpio} {consola.upper()}"
                        else:
                            nombre_busqueda = nombre_limpio
                        
                        self.stdout.write(f"\n{'='*60}")
                        self.stdout.write(f"PROCESANDO: '{nombre_sucio}' -> '{nombre_busqueda}'")
                        
                        # Obtener y limpiar precio
                        precio_str = row.get(col_precio, '').strip()
                        precio_secundario = self.limpiar_precio(precio_str)
                        recargo_secundario = self.calcular_recargo(precio_secundario)
                        
                        # Buscar juego existente
                        juego_existente = self.buscar_juego_similar(nombre_busqueda, consola)
                        
                        if juego_existente:
                            # ✅ CASO 1: JUEGO EXISTE - Agregar precio secundario
                            juego_existente.precio_secundario = precio_secundario
                            juego_existente.recargo_secundario = recargo_secundario
                            juego_existente.tiene_secundario = True
                            juego_existente.save()
                            
                            secundarios_ids.append(juego_existente.id)
                            actualizados_existentes += 1
                            
                            self.stdout.write(self.style.SUCCESS(
                                f'✅ AGREGADO PRECIO SECUNDARIO: {juego_existente.nombre}\n'
                                f'   Primario: ${juego_existente.precio} | Secundario: ${precio_secundario}'
                            ))
                        
                        else:
                            # ❌ CASO 2: JUEGO NO EXISTE - Crear nuevo en categoría secundarios
                            imagen = self.buscar_imagen(nombre_busqueda, consola)
                            
                            nuevo_juego = Juego.objects.create(
                                nombre=nombre_busqueda,
                                precio=precio_secundario,
                                recargo=recargo_secundario,
                                consola=consola,
                                disponible=True,
                                imagen=imagen,
                                es_solo_secundario=True,  # Marca especial para secundarios sin primario
                                precio_secundario=None,
                                recargo_secundario=None,
                                tiene_secundario=False
                            )
                            
                            secundarios_ids.append(nuevo_juego.id)
                            creados_nuevos += 1
                            
                            self.stdout.write(self.style.WARNING(
                                f'🆕 CREADO COMO SECUNDARIO NUEVO: {nuevo_juego.nombre}\n'
                                f'   Precio: ${precio_secundario}'
                            ))
                        
                    except Exception as e:
                        error_msg = f'Línea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        # Desactivar secundarios que ya no están en stock
        if secundarios_ids:
            # Desactivar solo los que tienen precio secundario y no están en la lista
            juegos_a_desactivar_secundario = Juego.objects.filter(
                consola=consola,
                tiene_secundario=True
            ).exclude(id__in=secundarios_ids)
            
            for juego in juegos_a_desactivar_secundario:
                juego.precio_secundario = None
                juego.recargo_secundario = None
                juego.tiene_secundario = False
                juego.save()
            
            desactivados_secundario_count = juegos_a_desactivar_secundario.count()
            
            # Desactivar juegos que son SOLO secundarios y no están en lista
            juegos_solo_secundarios = Juego.objects.filter(
                consola=consola,
                es_solo_secundario=True
            ).exclude(id__in=secundarios_ids)
            
            desactivados_solo_secundario = juegos_solo_secundarios.update(disponible=False)
        else:
            desactivados_secundario_count = 0
            desactivados_solo_secundario = 0
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE ACTUALIZACIÓN DE SECUNDARIOS'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Juegos con precio secundario agregado: {actualizados_existentes}'))
        self.stdout.write(self.style.WARNING(f'🆕 Juegos nuevos creados (solo secundarios): {creados_nuevos}'))
        self.stdout.write(self.style.ERROR(f'🔴 Precios secundarios eliminados: {desactivados_secundario_count}'))
        self.stdout.write(self.style.ERROR(f'🔴 Secundarios puros desactivados: {desactivados_solo_secundario}'))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\n❌ ERRORES: {len(errores)}'))
            for error in errores[:10]:
                self.stdout.write(f"  - {error}")